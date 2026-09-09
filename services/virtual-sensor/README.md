# Sensor virtual

Reproduz (*replay*) o dataset real do testbed publicando via MQTT nos **mesmos tópicos e
no mesmo formato de payload** que o nó ESP32 — ver o contrato de mensagens no
[README principal](../../README.md#contrato-de-mensagens-mqtt-preliminar).

Objetivo: validar toda a cadeia (ingestão → persistência → decisão → painel) antes do
hardware existir, e testar o que o hardware não deixa testar sob demanda.

Parâmetros previstos:

- `--fator-aceleracao` — quantas vezes mais rápido que o tempo real (10 min → 1 s, etc.);
- `--temporada` / `--linha` — recorte do dataset a reproduzir;
- `--perda-amostras` — fração de mensagens descartadas;
- `--ruido` — desvio-padrão do ruído aditivo por sensor;
- `--atraso` — atraso artificial de publicação;
- `--origem virtual` — prefixo do tópico, para não se confundir com o nó real.
