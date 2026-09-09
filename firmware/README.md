# Firmware do nó ESP32

Nó sensor/atuador em ESP32 (WROOM-32). Módulos independentes: aquisição, comunicação,
decisão e atuação — nenhum parâmetro operacional fixo no código.

**A decisão essencial roda aqui.** Sem Wi-Fi, sem broker e sem nuvem, o nó continua
irrigando com a última política válida e bufferiza a telemetria para sincronizar depois.

Intertravamentos de segurança (não negociáveis):

- desligamento incondicional da bomba ao atingir o tempo máximo por evento (padrão 60 s),
  reforçado por temporizador independente do laço principal;
- intervalo mínimo entre eventos de irrigação;
- bloqueio da atuação diante de leitura inválida de sensor;
- *watchdog*, com reinício em estado seguro (bomba desligada).

Sensores: umidade capacitiva do solo (v1.2, calibrada em dois pontos — seco e saturado),
DS18B20 (temperatura do solo), BME280 (temperatura, UR e pressão do ar), sensor de vazão.
