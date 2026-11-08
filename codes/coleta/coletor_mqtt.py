"""
Coletor MQTT da estação SIT.

Assina os tópicos da estação e grava tudo em CSV, para a análise e os gráficos da entrega.

  outputs/coleta/leituras.csv  uma linha por leitura publicada pelo ESP32
  outputs/coleta/eventos.csv   bomba ligada/desligada e status online/offline

Uso:
  pip install paho-mqtt
  python codes/coleta/coletor_mqtt.py

Deixe rodando enquanto a estação estiver ligada. Ctrl+C encerra.
Para irrigar pelo MQTT (sem o Serial Monitor), publique em <base>/bomba/cmd o número de segundos.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt

# ============================================================
# CONFIGURAÇÃO (tem que bater com o secrets.h e o firmware)
# ============================================================

MQTT_HOST = "broker.hivemq.com"
MQTT_PORTA = 8883  # TLS, igual ao firmware (secrets.h); a 1883 sem criptografia também funciona no HiveMQ
TOPICO_BASE = "sit/ufc-pi4/estacao01"

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "coleta"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ARQ_LEITURAS = OUTPUT_DIR / "leituras.csv"
ARQ_EVENTOS = OUTPUT_DIR / "eventos.csv"

CAMPOS_LEITURAS = ["recebido_em", "ts", "solo_bruto", "solo_pct", "temp_c", "umid_ar_pct", "rssi"]
CAMPOS_EVENTOS = ["recebido_em", "topico", "valor"]

# ============================================================


def anexar(arquivo, campos, linha):
    novo = not arquivo.exists()
    with open(arquivo, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        if novo:
            w.writeheader()
        w.writerow(linha)


def ao_conectar(client, userdata, flags, reason_code, properties):
    print(f"Conectado ao broker {MQTT_HOST} ({reason_code})")
    client.subscribe(f"{TOPICO_BASE}/#")


def ao_receber(client, userdata, msg):
    agora = datetime.now().isoformat(timespec="seconds")
    texto = msg.payload.decode("utf-8", errors="replace")

    if msg.topic.endswith("/leituras"):
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError:
            print(f"[{agora}] JSON inválido: {texto}")
            return
        linha = {"recebido_em": agora, **{c: dados.get(c) for c in CAMPOS_LEITURAS[1:]}}
        anexar(ARQ_LEITURAS, CAMPOS_LEITURAS, linha)
        print(f"[{agora}] solo {linha['solo_pct']}% (bruto {linha['solo_bruto']}) | "
              f"ar {linha['temp_c']} C {linha['umid_ar_pct']}%")
    elif not msg.topic.endswith("/bomba/cmd"):
        # status e estado da bomba; o comando em si não interessa, só o efeito
        anexar(ARQ_EVENTOS, CAMPOS_EVENTOS, {"recebido_em": agora, "topico": msg.topic, "valor": texto})
        print(f"[{agora}] {msg.topic} = {texto}")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = ao_conectar
    client.on_message = ao_receber
    if MQTT_PORTA in (8883, 8884):
        client.tls_set()  # certificados do sistema
    client.connect(MQTT_HOST, MQTT_PORTA, keepalive=60)
    print(f"Gravando em {OUTPUT_DIR}")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nColeta encerrada.")


if __name__ == "__main__":
    main()
