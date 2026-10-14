// Diagnóstico rápido: mostra GPIO4 e GPIO6 (ADC) a cada 0,5 s e o AM2302 no GPIO5 a cada 3 s.

#include <DHT.h>

DHT dht(5, DHT22);
unsigned long ultimoDht = 0;

int media(int p) {
  long s = 0;
  for (int i = 0; i < 10; i++) { s += analogRead(p); delay(2); }
  return s / 10;
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  dht.begin();
  Serial.println("\n=== DIAGNOSTICO G4/G6 ===");
}

void loop() {
  Serial.printf("G4=%d G6=%d", media(4), media(6));
  if (millis() - ultimoDht > 3000) {
    ultimoDht = millis();
    Serial.printf("  | AM2302: %.1f C %.1f %%", dht.readTemperature(), dht.readHumidity());
  }
  Serial.println();
  delay(500);
}
