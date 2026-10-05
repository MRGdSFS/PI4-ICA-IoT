// Irrigação automática: ESP32 + sensor capacitivo de umidade do solo v1.2 + BME280
//
// O modelo (modelo_irrigacao.h) é gerado pelo notebook
// codes/linha3 - umidade/modelo_linha3/modelo_irrigacao.ipynb. Os valores de calibração
// abaixo saem do procedimento da seção 9 do mesmo notebook.
//
// Bibliotecas (Arduino IDE > Gerenciador de bibliotecas):
//   - Adafruit BME280 Library
//   - Adafruit Unified Sensor
// Placa: ESP32 Dev Module (pacote "esp32" da Espressif).
//
// A cada 10 min: lê os sensores, calcula as features, roda o modelo e
// decide se abre a válvula. Cada leitura é impressa na Serial em CSV
// para que os dados de Fortaleza possam retreinar o modelo depois.

#include <WiFi.h>
#include <Wire.h>
#include <time.h>
#include <Adafruit_BME280.h>

#include "modelo_irrigacao.h"

// ------------------------------------------------------------------
// Wi-Fi: usado só para acertar o relógio (NTP). A hora solar é feature.
// ------------------------------------------------------------------
const char* WIFI_SSID = "SUA_REDE";
const char* WIFI_SENHA = "SUA_SENHA";

// ------------------------------------------------------------------
// Pinos
// ------------------------------------------------------------------
const int PINO_SOLO = 34;           // saída AOUT do sensor; use ADC1 (GPIO 32-39), o ADC2 não funciona com Wi-Fi
const int PINO_ALIMENTA_SOLO = 25;  // VCC do sensor: liga só na hora de ler
const int PINO_RELE = 26;           // relé da válvula solenoide / bomba
const bool RELE_LIGA_EM_ALTO = true;

// ------------------------------------------------------------------
// Calibração do sensor de solo (em mV, medir no próprio solo)
// ------------------------------------------------------------------
const float MV_SECO = 2600.0;  // solo seco (planta começando a murchar)
const float MV_CC = 1400.0;    // capacidade de campo (encharcado e drenado)

// Umidade relativa: 0 = seco, 100 = capacidade de campo.
// Tomate: irrigar quando ~40% da água disponível foi consumida (FAO-56, p = 0,40).
const float LIMIAR = 60.0;
const float ESCALA = 40.0;  // (umidade logo após irrigar) - LIMIAR; ajustar após a 1ª semana

const float LONGITUDE = -38.54;  // Fortaleza

// ------------------------------------------------------------------
// Irrigação
// ------------------------------------------------------------------
const unsigned long PULSO_MIN = 10;   // duração de cada pulso
const unsigned long ESPERA_MIN = 10;  // espera depois do pulso para a água infiltrar
const float PARAR_EM = LIMIAR + ESCALA / 2;  // repete pulsos até passar deste valor
const int MAX_PULSOS_DIA = 12;

const unsigned long CICLO_MS = 10UL * 60UL * 1000UL;  // o modelo foi treinado com dados a cada 10 min

// ------------------------------------------------------------------
// Estado
// ------------------------------------------------------------------
Adafruit_BME280 bme;
bool bmeOk = false;

const int N_HIST = 19;  // 3 h de histórico em passos de 10 min (0, 10, ..., 180 min)
float historico[N_HIST];
int leituras = 0;

bool valvulaAberta = false;
bool emEpisodio = false;
unsigned long inicioPulsoMs = 0;
unsigned long fimPulsoMs = 0;
time_t ultimaIrrigacao = 0;
int pulsosHoje = 0;
int diaAtual = -1;
unsigned long ultimoCicloMs = 0;

// ------------------------------------------------------------------

void abrirValvula(bool abrir) {
  digitalWrite(PINO_RELE, abrir == RELE_LIGA_EM_ALTO ? HIGH : LOW);
  valvulaAberta = abrir;
}

float lerSoloMv() {
  digitalWrite(PINO_ALIMENTA_SOLO, HIGH);
  delay(200);  // tempo para a saída do sensor estabilizar
  uint32_t soma = 0;
  const int n = 32;
  for (int i = 0; i < n; i++) {
    soma += analogReadMilliVolts(PINO_SOLO);
    delay(5);
  }
  digitalWrite(PINO_ALIMENTA_SOLO, LOW);
  return soma / (float)n;
}

float umidadeRelativa(float mv) {
  // mais seco = tensão maior
  float u = 100.0 * (MV_SECO - mv) / (MV_SECO - MV_CC);
  return constrain(u, -20.0, 130.0);
}

float vpd(float temp, float ur) {
  float es = 0.6108 * expf(17.27 * temp / (temp + 237.3));
  return es * (1.0 - ur / 100.0);
}

// Umidade de k passos atrás (k = 0 é a leitura atual)
float umidadeAtras(int k) {
  return historico[(leituras - 1 - k) % N_HIST];
}

void guardarHistorico(float u) {
  historico[leituras % N_HIST] = u;
  leituras++;
}

void setup() {
  Serial.begin(115200);

  pinMode(PINO_RELE, OUTPUT);
  pinMode(PINO_ALIMENTA_SOLO, OUTPUT);
  abrirValvula(false);
  analogSetPinAttenuation(PINO_SOLO, ADC_11db);  // faixa de ~0 a 3,1 V

  Wire.begin();
  bmeOk = bme.begin(0x76) || bme.begin(0x77);
  if (!bmeOk) {
    // Placas BMP280 são parecidas com a BME280, mas não medem umidade.
    Serial.println("# BME280 não encontrado (confira se não é um BMP280). Rodando só com a regra de limiar.");
  }

  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  Serial.print("# Conectando ao Wi-Fi");
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  configTzTime("<-03>3", "pool.ntp.org", "a.st1.ntp.br");  // Fortaleza: UTC-3, sem horário de verão
  struct tm agora;
  if (!getLocalTime(&agora, 20000)) {
    Serial.println("# Sem hora certa (NTP). A hora solar vai ficar errada até sincronizar.");
  }

  Serial.println("data_hora,solo_mv,umidade,ar_temp,ar_ur,vpd,probabilidade,decisao,valvula");
  ultimoCicloMs = millis() - CICLO_MS;  // faz o primeiro ciclo já
}

void ciclo() {
  time_t agora = time(nullptr);
  struct tm local;
  localtime_r(&agora, &local);

  if (local.tm_yday != diaAtual) {
    diaAtual = local.tm_yday;
    pulsosHoje = 0;
  }

  // ---------------- Leituras
  float mv = lerSoloMv();
  float u = umidadeRelativa(mv);
  guardarHistorico(u);

  float temp = NAN, ur = NAN;
  if (bmeOk) {
    temp = bme.readTemperature();
    ur = bme.readHumidity();
  }

  // ---------------- Features (mesma ordem do notebook)
  float prob = NAN;
  bool historicoCompleto = leituras >= N_HIST;

  if (historicoCompleto && bmeOk && !isnan(temp) && !isnan(ur)) {
    float horaUtc = (agora % 86400) / 3600.0;
    float horaSolar = fmodf(horaUtc + LONGITUDE / 15.0 + 24.0, 24.0);
    float horasDesde = ultimaIrrigacao == 0 ? 48.0 : min(48.0, (agora - ultimaIrrigacao) / 3600.0);

    float x[N_FEATURES] = {
      (u - LIMIAR) / ESCALA,                  // dist_limiar
      (u - umidadeAtras(3)) / ESCALA,         // tend_30min
      (u - umidadeAtras(6)) / ESCALA,         // tend_60min
      (u - umidadeAtras(18)) / ESCALA,        // tend_180min
      temp,                                   // ar_temperatura
      ur,                                     // ar_umidade
      vpd(temp, ur),                          // vpd_kpa
      sinf(2 * PI * horaSolar / 24),          // hora_solar_sin
      cosf(2 * PI * horaSolar / 24),          // hora_solar_cos
      horasDesde,                             // horas_desde_irrigacao
    };
    prob = modelo_probabilidade(x);
  }

  // ---------------- Decisão
  const char* decisao = "esperar";
  bool emEspera = fimPulsoMs != 0 && millis() - fimPulsoMs < ESPERA_MIN * 60000UL;

  if (valvulaAberta) {
    decisao = "irrigando";
  } else if (emEspera) {
    decisao = "infiltrando";
  } else if (pulsosHoje >= MAX_PULSOS_DIA) {
    decisao = "limite_diario";
  } else if (u <= LIMIAR) {
    decisao = "irrigar_limiar";  // regra de segurança, igual ao controlador de Parma
  } else if (emEpisodio && u < PARAR_EM) {
    decisao = "irrigar_completar";  // repete pulsos até a umidade subir
  } else if (!isnan(prob) && prob >= MODELO_CORTE && u < PARAR_EM) {
    decisao = "irrigar_antecipado";  // o modelo prevê irrigação na próxima hora
  } else {
    emEpisodio = false;
  }

  if (strncmp(decisao, "irrigar", 7) == 0) {
    abrirValvula(true);
    inicioPulsoMs = millis();
    emEpisodio = true;
    pulsosHoje++;
    ultimaIrrigacao = agora;
  }

  // ---------------- Registro (CSV na Serial)
  char dataHora[25];
  strftime(dataHora, sizeof(dataHora), "%Y-%m-%d %H:%M:%S", &local);
  Serial.printf("%s,%.0f,%.1f,%.1f,%.1f,%.2f,%.3f,%s,%d\n",
                dataHora, mv, u, temp, ur, isnan(temp) ? NAN : vpd(temp, ur),
                prob, decisao, valvulaAberta ? 1 : 0);
}

void loop() {
  // fecha a válvula no fim do pulso
  if (valvulaAberta && millis() - inicioPulsoMs >= PULSO_MIN * 60000UL) {
    abrirValvula(false);
    fimPulsoMs = millis();
    ultimaIrrigacao = time(nullptr);
  }

  if (millis() - ultimoCicloMs >= CICLO_MS) {
    ultimoCicloMs += CICLO_MS;
    ciclo();
  }

  delay(200);
}
