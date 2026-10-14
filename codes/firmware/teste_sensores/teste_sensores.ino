// Teste de bancada: ESP32-S3 + Capacitive Soil Moisture Sensor v2.0 + AM2302 (DHT22)
//
// Ligações:
//   Sensor de solo  VCC -> 3V3 | GND -> GND | AOUT -> GPIO4
//   AM2302          VCC (vermelho) -> 3V3 | GND (preto) -> GND | DATA (amarelo) -> GPIO5
//
// Bibliotecas (Arduino IDE > Gerenciador de Bibliotecas):
//   "DHT sensor library" (Adafruit) + "Adafruit Unified Sensor"

#include <DHT.h>

#define PINO_SOLO 4   // ADC1 (o ADC2 não funciona junto com o Wi-Fi)
#define PINO_DHT  5
#define TIPO_DHT  DHT22  // AM2302 = DHT22

// Calibração: ajuste com os valores lidos no seu sensor
#define SOLO_SECO    3000  // leitura com o sensor no ar
#define SOLO_MOLHADO 1300  // leitura com o sensor dentro de um copo d'água

DHT dht(PINO_DHT, TIPO_DHT);

int lerSoloMedia(int amostras) {
  long soma = 0;
  for (int i = 0; i < amostras; i++) {
    soma += analogRead(PINO_SOLO);
    delay(10);
  }
  return soma / amostras;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  analogReadResolution(12);        // 0..4095
  analogSetAttenuation(ADC_11db);  // faixa de ~0 a 3,1 V
  dht.begin();
  Serial.println("Teste de sensores iniciado");
}

void loop() {
  int bruto = lerSoloMedia(20);
  int umidadeSolo = constrain(map(bruto, SOLO_SECO, SOLO_MOLHADO, 0, 100), 0, 100);

  float temperatura = dht.readTemperature();
  float umidadeAr = dht.readHumidity();

  Serial.printf("Solo: bruto=%d  umidade=%d%%  |  ", bruto, umidadeSolo);
  if (isnan(temperatura) || isnan(umidadeAr)) {
    Serial.println("AM2302: falha na leitura (confira fios / pull-up)");
  } else {
    Serial.printf("Ar: %.1f C  %.1f%%\n", temperatura, umidadeAr);
  }

  delay(2000);  // o AM2302 precisa de pelo menos 2 s entre leituras
}
