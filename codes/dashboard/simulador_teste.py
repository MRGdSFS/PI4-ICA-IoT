"""
Simulador de TESTE do painel SIT (codes/dashboard/index.html).

Publica DADOS DE TESTE (sintéticos, NÃO medidos) num tópico separado, no mesmo formato do
firmware, para ensaiar a apresentação e testar o painel sem a estação.
Nunca publica no tópico real (sit/ufc-pi4/estacao01): o script se recusa.

Uso:
  python codes/dashboard/simulador_teste.py                  (1 leitura a cada 30 s, como o firmware)
  python codes/dashboard/simulador_teste.py --intervalo 3    (mais rápido, para ensaio)
  python codes/dashboard/simulador_teste.py --historico 60   (antes, manda 30 min de leituras de teste com ts no passado)
  python codes/dashboard/simulador_teste.py --limpar         (só apaga as mensagens retidas do tópico de teste)

Depois abra o painel apontando para o tópico de teste:
  codes/dashboard/index.html?base=sit/ufc-pi4/teste-dashboard

O que ele faz:
  <base>/leituras      JSON igual ao do firmware, a cada --intervalo segundos
  <base>/status        "online" retido; "offline" como last will (igual à estação)
  <base>/bomba/estado  "ligada"/"desligada" retido
  <base>/bomba/cmd     responde como o firmware: liga N s (no máximo 5) e desliga sozinho;
                       a umidade simulada do solo sobe a cada rega e desce devagar entre as leituras

Porta padrão 8000 (MQTT sobre WebSocket), que passa em redes que bloqueiam a 1883.
Ctrl+C encerra e publica "offline" no status.
"""

import argparse
import json
import math
import random
import re
import sys
import threading
import time

import paho.mqtt.client as mqtt

BASE_REAL = "sit/ufc-pi4/estacao01"
BASE_TESTE = "sit/ufc-pi4/teste-dashboard"
HOST = "broker.hivemq.com"
SOLO_SECO, SOLO_MOLHADO = 3560, 1300  # mesma calibração do firmware
BOMBA_MAX_S = 3


def criar_cliente(porta, base):
    transporte = "websockets" if porta in (8000, 8884) else "tcp"
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"sit-simulador-teste-{random.randrange(16**6):06x}",
                    transport=transporte)
    if transporte == "websockets":
        c.ws_set_options(path="/mqtt")
    if porta in (8883, 8884):
        c.tls_set()
    c.will_set(f"{base}/status", "offline", qos=1, retain=True)
    return c


def segundos_do_comando(texto):
    # o firmware usa atol(): pega o inteiro do começo ("2.7" vira 2, "abc" vira 0)
    m = re.match(r"\s*[-+]?\d+", texto)
    return int(m.group()) if m else 0


def main():
    ap = argparse.ArgumentParser(description="Publica DADOS DE TESTE para o painel SIT (nunca no tópico real).")
    ap.add_argument("--base", default=BASE_TESTE, help=f"tópico base de teste (padrão {BASE_TESTE})")
    ap.add_argument("--intervalo", type=float, default=30.0, help="segundos entre leituras (padrão 30, como o firmware)")
    ap.add_argument("--porta", type=int, default=8000, choices=[1883, 8000, 8883, 8884],
                    help="8000 = WebSocket (padrão), 1883 = TCP, 8883 = TCP com TLS, 8884 = WebSocket com TLS")
    ap.add_argument("--solo-inicial", type=float, default=57.0, help="umidade simulada do solo no início (%%)")
    ap.add_argument("--secagem", type=float, default=0.35, help="quanto o solo simulado seca por leitura (pontos de %%)")
    ap.add_argument("--historico", type=int, default=0,
                    help="antes de começar, publica N leituras de teste com ts no passado (30 s entre elas)")
    ap.add_argument("--duracao", type=float, default=0, help="encerra sozinho depois de N s (0 = até Ctrl+C)")
    ap.add_argument("--registro", help="arquivo .jsonl para guardar cada leitura publicada (para conferir testes)")
    ap.add_argument("--limpar", action="store_true", help="só apaga as mensagens retidas do tópico de teste e sai")
    args = ap.parse_args()

    base = args.base.strip().rstrip("/")
    if base == BASE_REAL or not base.startswith("sit/ufc-pi4/teste") or any(ch in base for ch in "#+"):
        sys.exit("Recusado: o simulador só publica em tópicos de teste (sit/ufc-pi4/teste...), nunca no tópico real.")

    c = criar_cliente(args.porta, base)

    if args.limpar:
        conectado = threading.Event()
        c.on_connect = lambda cli, u, f, rc, p: conectado.set()
        c.connect(HOST, args.porta, keepalive=30)
        c.loop_start()
        if not conectado.wait(15):
            sys.exit("Não conectou ao broker.")
        for t in ("status", "bomba/estado"):
            c.publish(f"{base}/{t}", b"", qos=1, retain=True).wait_for_publish(10)
        c.disconnect()
        c.loop_stop()
        print(f"Mensagens retidas apagadas em {base}/status e {base}/bomba/estado.")
        return

    trava = threading.Lock()
    estado = {"solo": args.solo_inicial, "timer": None, "ligada": False}

    def desligar():
        with trava:
            if estado["timer"]:
                estado["timer"].cancel()
            estado["timer"] = None
            estado["ligada"] = False
        c.publish(f"{base}/bomba/estado", "desligada", qos=1, retain=True)
        print("[DADOS DE TESTE] bomba desligada")

    def ao_conectar(cli, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"Falha ao conectar: {reason_code}")
            return
        cli.publish(f"{base}/status", "online", qos=1, retain=True)
        cli.publish(f"{base}/bomba/estado", "ligada" if estado["ligada"] else "desligada", qos=1, retain=True)
        cli.subscribe(f"{base}/bomba/cmd")
        print(f"Conectado a {HOST}:{args.porta}. Publicando DADOS DE TESTE em {base}/# (Ctrl+C encerra)")

    def ao_receber(cli, userdata, msg):
        if msg.topic != f"{base}/bomba/cmd":
            return
        texto = msg.payload.decode("utf-8", errors="replace")
        seg = segundos_do_comando(texto)
        print(f"[DADOS DE TESTE] comando recebido em bomba/cmd: {texto!r}")
        if seg <= 0:
            desligar()
            return
        dur = min(seg, BOMBA_MAX_S)
        with trava:
            if estado["timer"]:
                estado["timer"].cancel()
            estado["ligada"] = True
            estado["solo"] = min(97.0, estado["solo"] + 7.5 * dur)  # cada segundo de rega molha ~7,5 pontos
            estado["timer"] = threading.Timer(dur, desligar)
            estado["timer"].daemon = True
            estado["timer"].start()
        cli.publish(f"{base}/bomba/estado", "ligada", qos=1, retain=True)
        print(f"[DADOS DE TESTE] bomba ligada por {dur} s")

    c.on_connect = ao_conectar
    c.on_message = ao_receber
    c.connect(HOST, args.porta, keepalive=30)
    c.loop_start()

    registro = open(args.registro, "a", encoding="utf-8") if args.registro else None

    def publicar_leitura(k, ts):
        with trava:
            estado["solo"] = max(5.0, estado["solo"] - args.secagem + random.uniform(-0.25, 0.25))
            pct_real = estado["solo"]
        bruto = round(SOLO_SECO - pct_real / 100 * (SOLO_SECO - SOLO_MOLHADO) + random.uniform(-6, 6))
        solo_pct = max(0, min(100, int((bruto - SOLO_SECO) * 100 / (SOLO_MOLHADO - SOLO_SECO))))  # map() do firmware
        leitura = {
            "ts": int(ts),
            "solo_bruto": bruto,
            "solo_pct": solo_pct,
            "temp_c": round(26.0 + 1.6 * math.sin(k / 12) + random.uniform(-0.15, 0.15), 1),
            "umid_ar_pct": round(66.0 - 5.0 * math.sin(k / 12) + random.uniform(-0.4, 0.4), 1),
            "rssi": int(round(-61 + random.uniform(-5, 4))),
        }
        texto = json.dumps(leitura, separators=(",", ":"))
        if not c.is_connected():
            print("  (desconectado do broker, leitura de teste não enviada)")
            return
        c.publish(f"{base}/leituras", texto)
        if registro:
            registro.write(texto + "\n")
            registro.flush()
        print(f"[DADOS DE TESTE] {texto}")

    # espera conectar antes de publicar
    for _ in range(300):
        if c.is_connected():
            break
        time.sleep(0.05)

    k = 0
    if args.historico:
        # "histórico" de teste: N leituras com ts no passado, a cada 30 s, publicadas em sequência rápida
        agora = time.time()
        for i in range(args.historico):
            publicar_leitura(k, agora - (args.historico - i) * 30)
            k += 1
            time.sleep(0.12)

    inicio = time.time()
    proxima = time.time() + 1.0
    try:
        while not args.duracao or time.time() - inicio < args.duracao:
            if time.time() < proxima:
                time.sleep(0.05)
                continue
            proxima += args.intervalo
            publicar_leitura(k, time.time())
            k += 1
    except KeyboardInterrupt:
        pass
    finally:
        if registro:
            registro.close()
        if c.is_connected():
            c.publish(f"{base}/status", "offline", qos=1, retain=True).wait_for_publish(5)
        c.disconnect()
        c.loop_stop()
        print("\nSimulador encerrado (status de teste = offline).")


if __name__ == "__main__":
    main()
