// Copie este arquivo para "secrets.h" (mesma pasta) e preencha.
// O secrets.h está no .gitignore e não vai para o GitHub.
#pragma once

#define WIFI_SSID  "nome-da-rede"
#define WIFI_SENHA "senha-da-rede"

// Broker público para testes. Qualquer pessoa pode ler/publicar nele.
#define MQTT_HOST    "broker.hivemq.com"
#define MQTT_PORTA   8883  // TLS; a 1883 costuma ser bloqueada em redes de universidade
#define MQTT_USUARIO ""
#define MQTT_SENHA   ""
