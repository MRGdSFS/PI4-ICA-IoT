// SIT - estação de coleta e irrigação
// ESP32-S3 + sensor capacitivo de solo v2.0 + AM2302 (DHT22) + bomba 5 V chaveada por transistor NPN
//
// Ligações:
//   Sensor de solo  VCC -> 3V3 | GND -> GND | AOUT -> GPIO4
//   AM2302          VCC -> 3V3 | GND -> GND | DATA -> GPIO5
//   Transistor NPN MPSA42 (E-B-C): base <- resistor 1 kΩ <- GPIO6 | emissor -> GND | coletor -> fio preto da bomba
//   Bomba 5 V (JT100): fio vermelho -> 5V | fio preto -> coletor
//   Diodo 1N4007 em paralelo com a bomba: listra (catodo) no 5V, outro lado no coletor
//
// Bibliotecas: "DHT sensor library" + "Adafruit Unified Sensor" (Adafruit), "PubSubClient" (Nick O'Leary)
//
// Tópicos MQTT (TOPICO_BASE = sit/ufc-pi4/estacao01):
//   <base>/leituras      publica JSON a cada INTERVALO_LEITURA_MS
//   <base>/status        "online" / "offline" (retido, com last will)
//   <base>/bomba/cmd     recebe segundos de irrigação ("10" liga por 10 s, "0" desliga)
//   <base>/bomba/estado  "ligada" / "desligada" (retido)
//
// Comandos pelo Serial Monitor: "l" = leitura agora, número = liga a bomba por N segundos

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <time.h>
#include <esp_timer.h>
#include "secrets.h"

// ---------- Pinos ----------
#define PINO_SOLO 4  // ADC1 (o ADC2 não funciona junto com o Wi-Fi)
#define PINO_DHT  5
#define PINO_RELE 6  // base do transistor (o nome ficou do módulo relé)
#define TIPO_DHT  DHT22
#define RELE_ATIVO_BAIXO false  // transistor NPN liga com HIGH; use true se trocar por módulo relé

// ---------- Calibração do sensor de solo ----------
#define SOLO_SECO    3560  // medido no ar
#define SOLO_MOLHADO 1300  // TODO: medir com o sensor dentro da água

// ---------- Tempos ----------
const unsigned long INTERVALO_LEITURA_MS = 30UL * 1000;       // 30 s na coleta da v1; 10 min depois
const unsigned long BOMBA_MAX_MS = 3UL * 1000;                // trava por acionamento: 3 s já encharcaram o vaso de 10 cm; use 1 s por rega
const unsigned long RECONEXAO_MQTT_MS = 5000;

// ---------- MQTT ----------
#define TOPICO_BASE "sit/ufc-pi4/estacao01"
const char* TOPICO_LEITURAS    = TOPICO_BASE "/leituras";
const char* TOPICO_STATUS      = TOPICO_BASE "/status";
const char* TOPICO_BOMBA_CMD   = TOPICO_BASE "/bomba/cmd";
const char* TOPICO_BOMBA_ESTADO = TOPICO_BASE "/bomba/estado";

DHT dht(PINO_DHT, TIPO_DHT);
WiFiClientSecure wifiClient;  // MQTT com TLS (porta 8883): muitas redes bloqueiam a 1883
PubSubClient mqtt(wifiClient);

unsigned long ultimaLeitura = 0;
bool primeiraLeitura = true;
unsigned long ultimaTentativaMqtt = 0;
bool bombaLigada = false;
unsigned long bombaDesligarEm = 0;
esp_timer_handle_t timerBomba = nullptr;  // desliga a bomba por hardware, mesmo se o loop travar

// ---------- Bomba ----------

void escreverRele(bool ligar) {
  digitalWrite(PINO_RELE, (ligar != RELE_ATIVO_BAIXO) ? HIGH : LOW);
}

void setBomba(bool ligar, unsigned long duracaoMs = 0) {
  if (ligar) {
    duracaoMs = min(duracaoMs, BOMBA_MAX_MS);
    bombaDesligarEm = millis() + duracaoMs;
    esp_timer_stop(timerBomba);
    esp_timer_start_once(timerBomba, (uint64_t)duracaoMs * 1000);
  } else {
    esp_timer_stop(timerBomba);
  }
  bombaLigada = ligar;
  escreverRele(ligar);
  Serial.printf("Bomba %s", ligar ? "LIGADA" : "desligada");
  if (ligar) Serial.printf(" por %lu s", duracaoMs / 1000);
  Serial.println();
  if (mqtt.connected()) mqtt.publish(TOPICO_BOMBA_ESTADO, ligar ? "ligada" : "desligada", true);
}

// ---------- Sensores ----------

int lerSoloMedia(int amostras) {
  long soma = 0;
  for (int i = 0; i < amostras; i++) {
    soma += analogRead(PINO_SOLO);
    delay(10);
  }
  return soma / amostras;
}

void fazerLeitura() {
  int bruto = lerSoloMedia(20);
  int umidadeSolo = constrain(map(bruto, SOLO_SECO, SOLO_MOLHADO, 0, 100), 0, 100);
  float temperatura = dht.readTemperature();
  float umidadeAr = dht.readHumidity();
  time_t agora = time(nullptr);

  char ts[16], temp[12], umid[12];
  if (agora > 1700000000) snprintf(ts, sizeof(ts), "%ld", (long)agora); else strcpy(ts, "null");
  if (isnan(temperatura)) strcpy(temp, "null"); else snprintf(temp, sizeof(temp), "%.1f", temperatura);
  if (isnan(umidadeAr))   strcpy(umid, "null"); else snprintf(umid, sizeof(umid), "%.1f", umidadeAr);

  char json[200];
  snprintf(json, sizeof(json),
           "{\"ts\":%s,\"solo_bruto\":%d,\"solo_pct\":%d,\"temp_c\":%s,\"umid_ar_pct\":%s,\"rssi\":%d}",
           ts, bruto, umidadeSolo, temp, umid, WiFi.RSSI());

  Serial.println(json);
  if (mqtt.connected()) {
    mqtt.publish(TOPICO_LEITURAS, json);
  } else {
    Serial.println("  (MQTT desconectado, leitura não enviada)");
  }
}

// ---------- Rede ----------

void aoReceberMqtt(char* topico, byte* payload, unsigned int tamanho) {
  char msg[16];
  tamanho = min(tamanho, (unsigned int)sizeof(msg) - 1);
  memcpy(msg, payload, tamanho);
  msg[tamanho] = '\0';
  Serial.printf("MQTT %s: %s\n", topico, msg);

  if (strcmp(topico, TOPICO_BOMBA_CMD) == 0) {
    long segundos = atol(msg);
    if (segundos > 0) setBomba(true, segundos * 1000UL);
    else setBomba(false);
  }
}

void garantirMqtt() {
  if (WiFi.status() != WL_CONNECTED || mqtt.connected()) return;
  if (millis() - ultimaTentativaMqtt < RECONEXAO_MQTT_MS) return;
  ultimaTentativaMqtt = millis();

  String clientId = "sit-estacao01-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  Serial.printf("Conectando ao MQTT %s... ", MQTT_HOST);
  bool ok = strlen(MQTT_USUARIO) > 0
    ? mqtt.connect(clientId.c_str(), MQTT_USUARIO, MQTT_SENHA, TOPICO_STATUS, 1, true, "offline")
    : mqtt.connect(clientId.c_str(), TOPICO_STATUS, 1, true, "offline");

  if (ok) {
    Serial.println("ok");
    mqtt.publish(TOPICO_STATUS, "online", true);
    mqtt.publish(TOPICO_BOMBA_ESTADO, bombaLigada ? "ligada" : "desligada", true);
    mqtt.subscribe(TOPICO_BOMBA_CMD);
  } else {
    Serial.printf("falhou (estado %d)\n", mqtt.state());
  }
}

void lerSerial() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd == "l") fazerLeitura();
  else if (cmd.length() > 0 && isDigit(cmd[0])) {
    long segundos = cmd.toInt();
    if (segundos > 0) setBomba(true, segundos * 1000UL); else setBomba(false);
  }
}

// ---------- Principal ----------

void setup() {
  escreverRele(false);  // antes do pinMode, para a bomba não dar um pulso no boot
  pinMode(PINO_RELE, OUTPUT);
  esp_timer_create_args_t args = {};
  args.callback = [](void*) { escreverRele(false); };
  args.name = "bomba";
  esp_timer_create(&args, &timerBomba);

  Serial.begin(115200);
  Serial.setTxTimeoutMs(0);  // USB nativa: nunca travar o loop esperando o PC ler o Serial
  delay(1000);
  Serial.println("\nSIT - estação iniciada");

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  dht.begin();

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  Serial.printf("Conectando ao Wi-Fi %s", WIFI_SSID);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf(" ok, IP %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println(" falhou (seguindo e tentando de novo em segundo plano)");
  }

  configTzTime("<-03>3", "a.st1.ntp.br", "pool.ntp.org");  // horário de Brasília
  wifiClient.setInsecure();  // broker público de testes: criptografa sem validar certificado
  mqtt.setServer(MQTT_HOST, MQTT_PORTA);
  mqtt.setCallback(aoReceberMqtt);
  mqtt.setBufferSize(512);
}

void loop() {
  garantirMqtt();
  mqtt.loop();
  lerSerial();

  if (bombaLigada && (long)(millis() - bombaDesligarEm) >= 0) setBomba(false);

  // primeira leitura só depois de conectar (ou 30 s sem rede), para já sair com horário
  bool prontoPrimeira = mqtt.connected() || millis() > 30000;
  if ((primeiraLeitura && prontoPrimeira) || (!primeiraLeitura && millis() - ultimaLeitura >= INTERVALO_LEITURA_MS)) {
    primeiraLeitura = false;
    ultimaLeitura = millis();
    fazerLeitura();
  }
}
