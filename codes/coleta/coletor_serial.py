"""
Coletor pela USB (serial) da estação SIT. Funciona sem Wi-Fi.

Lê as linhas JSON que o firmware imprime no Serial e grava no mesmo formato do coletor MQTT,
para o graficos.py funcionar igual:
  outputs/coleta/leituras.csv
  outputs/coleta/eventos.csv   (bomba ligada/desligada)

Para mandar um comando ao ESP32 com o coletor rodando (ex.: ligar a bomba 3 s),
escreva o comando no arquivo outputs/coleta/comando.txt; o coletor envia e apaga o arquivo.

Uso:
  python codes/coleta/coletor_serial.py            (acha a porta da ESP32 sozinho)
  python codes/coleta/coletor_serial.py --porta COM11
"""

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

import serial
import serial.tools.list_ports

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "coleta"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ARQ_LEITURAS = OUTPUT_DIR / "leituras.csv"
ARQ_EVENTOS = OUTPUT_DIR / "eventos.csv"
ARQ_COMANDO = OUTPUT_DIR / "comando.txt"
ARQ_LOG = OUTPUT_DIR / "serial_bruto.log"

CAMPOS_LEITURAS = ["recebido_em", "ts", "solo_bruto", "solo_pct", "temp_c", "umid_ar_pct", "rssi"]
CAMPOS_EVENTOS = ["recebido_em", "topico", "valor"]
TOPICO_BOMBA = "sit/ufc-pi4/estacao01/bomba/estado"


def anexar(arquivo, campos, linha):
    novo = not arquivo.exists()
    with open(arquivo, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        if novo:
            w.writeheader()
        w.writerow(linha)


def achar_porta():
    for p in serial.tools.list_ports.comports():
        if p.vid in (0x303A, 0x10C4, 0x1A86):  # Espressif nativo, CP210x, CH34x
            return p.device
    raise SystemExit("ESP32 não encontrada. Use --porta COMx.")


def abrir(porta):
    while True:
        try:
            return serial.Serial(porta, 115200, timeout=1)
        except serial.SerialException:
            print(f"Esperando {porta}...")
            time.sleep(2)


def tratar(linha):
    agora = datetime.now().isoformat(timespec="seconds")
    if linha.startswith("{"):
        try:
            dados = json.loads(linha)
        except json.JSONDecodeError:
            return
        if dados.get("tipo") == "evento":
            anexar(ARQ_EVENTOS, CAMPOS_EVENTOS, {"recebido_em": agora, "topico": TOPICO_BOMBA, "valor": dados.get("bomba")})
            print(f"[{agora}] bomba {dados.get('bomba')}")
            return
        if "solo_bruto" in dados:
            anexar(ARQ_LEITURAS, CAMPOS_LEITURAS, {"recebido_em": agora, **{c: dados.get(c) for c in CAMPOS_LEITURAS[1:]}})
            print(f"[{agora}] solo {dados.get('solo_pct')}% (bruto {dados.get('solo_bruto')}) | "
                  f"ar {dados.get('temp_c')} C {dados.get('umid_ar_pct')}%")
    elif linha.startswith("Bomba "):
        # firmware v1.0 imprime "Bomba LIGADA por N s" / "Bomba desligada"
        valor = "ligada" if "LIGADA" in linha else "desligada"
        anexar(ARQ_EVENTOS, CAMPOS_EVENTOS, {"recebido_em": agora, "topico": TOPICO_BOMBA, "valor": valor})
        print(f"[{agora}] {linha}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--porta")
    args = ap.parse_args()
    porta = args.porta or achar_porta()
    s = abrir(porta)
    print(f"Coletando de {porta} em {OUTPUT_DIR} (Ctrl+C encerra)")
    with open(ARQ_LOG, "a", encoding="utf-8") as log:
        while True:
            try:
                if ARQ_COMANDO.exists():
                    cmd = ARQ_COMANDO.read_text(encoding="utf-8").strip()
                    ARQ_COMANDO.unlink()
                    if cmd:
                        s.write((cmd + "\n").encode())
                        print(f">> comando enviado: {cmd}")
                bruto = s.readline()
                if not bruto:
                    continue
                linha = bruto.decode("utf-8", errors="replace").strip()
                log.write(f"{datetime.now().isoformat(timespec='seconds')} {linha}\n")
                log.flush()
                tratar(linha)
            except serial.SerialException:
                print("Porta caiu, reconectando...")
                s.close()
                time.sleep(2)
                s = abrir(porta)
            except KeyboardInterrupt:
                print("\nColeta encerrada.")
                break


if __name__ == "__main__":
    main()
