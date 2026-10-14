"""
Gráficos e resumo da coleta da estação SIT (entrega v1).

Lê o que o coletor_mqtt.py gravou e gera, na mesma pasta:
  serie_temporal.png   umidade do solo, temperatura e umidade do ar, com as irrigações marcadas
  comunicacao.png      RSSI do Wi-Fi e intervalo entre mensagens MQTT recebidas
  resumo.txt           período, número de leituras, perda de mensagens, estatísticas por variável

Irrigação feita à mão (copo d'água, antes da bomba funcionar) entra pelo arquivo opcional
irrigacoes_manuais.csv, com uma linha por rega:
  data_hora,volume_ml
  2026-10-12T14:30:00,100

Uso:
  python codes/coleta/graficos.py
  python codes/coleta/graficos.py --intervalo 60     (intervalo de leitura do firmware, em segundos)
"""

import argparse
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
COLETA_DIR = BASE_DIR / "outputs" / "coleta"

COR_SERIE = "#2a78d6"
COR_EVENTO = "#8a8984"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
GRADE = "#e4e3df"

plt.rcParams.update({
    "font.size": 10,
    "axes.edgecolor": GRADE,
    "axes.labelcolor": TINTA_2,
    "axes.titlecolor": TINTA,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "xtick.color": TINTA_2,
    "ytick.color": TINTA_2,
    "axes.grid": True,
    "grid.color": GRADE,
    "grid.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def carregar(pasta):
    leituras = pd.read_csv(pasta / "leituras.csv", parse_dates=["recebido_em"])
    # horário do ESP32 (NTP) quando existe; senão, o de chegada no coletor
    ts = pd.to_datetime(leituras["ts"], unit="s", errors="coerce", utc=True)
    ts = ts.where(ts > pd.Timestamp("2024-01-01", tz="UTC"))  # relógio sem NTP vira chegada
    leituras["hora"] = ts.dt.tz_convert("America/Fortaleza").dt.tz_localize(None).fillna(leituras["recebido_em"])
    leituras = leituras.sort_values("hora").reset_index(drop=True)

    irrigacoes = []
    eventos_arq = pasta / "eventos.csv"
    if eventos_arq.exists():
        ev = pd.read_csv(eventos_arq, parse_dates=["recebido_em"])
        ligou = ev[ev["topico"].str.endswith("/bomba/estado") & (ev["valor"] == "ligada")]
        irrigacoes += [(t, "bomba") for t in ligou["recebido_em"]]
    manuais_arq = pasta / "irrigacoes_manuais.csv"
    if manuais_arq.exists():
        man = pd.read_csv(manuais_arq, parse_dates=["data_hora"])
        irrigacoes += [(t, "manual") for t in man["data_hora"]]

    # descarta eventos fora da janela coletada (ex.: estado retido reenviado ao reconectar)
    ini, fim = leituras["hora"].min(), leituras["hora"].max()
    irrigacoes = sorted((t, o) for t, o in irrigacoes if ini <= t <= fim)
    return leituras, irrigacoes


def marcar_irrigacoes(ax, irrigacoes, rotular):
    for i, (t, origem) in enumerate(irrigacoes):
        ax.axvline(t, color=COR_EVENTO, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
        if rotular and i == 0:
            ax.annotate("irrigação", (t, 1), xycoords=("data", "axes fraction"),
                        xytext=(4, -2), textcoords="offset points", va="top",
                        color=TINTA_2, fontsize=9)


def serie_temporal(leituras, irrigacoes, pasta):
    paineis = [
        ("solo_pct", "Umidade do solo", "%"),
        ("temp_c", "Temperatura do ar", "°C"),
        ("umid_ar_pct", "Umidade relativa do ar", "%"),
    ]
    fig, eixos = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    for i, (ax, (col, titulo, unidade)) in enumerate(zip(eixos, paineis)):
        marcar_irrigacoes(ax, irrigacoes, rotular=(i == 0))
        ax.plot(leituras["hora"], leituras[col], color=COR_SERIE, linewidth=2, zorder=2)
        ax.set_title(titulo)
        ax.set_ylabel(unidade)
    eixos[0].set_ylim(0, 100)
    eixos[-1].xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(pasta / "serie_temporal.png", dpi=150)
    plt.close(fig)


def comunicacao(leituras, pasta):
    intervalo_min = leituras["recebido_em"].diff().dt.total_seconds() / 60
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    # bruto ao fundo, mediana móvel por cima (o RSSI oscila muito de uma leitura para outra)
    a1.plot(leituras["recebido_em"], leituras["rssi"], color=COR_SERIE, linewidth=0.8, alpha=0.25)
    a1.plot(leituras["recebido_em"], leituras["rssi"].rolling(15, center=True, min_periods=1).median(),
            color=COR_SERIE, linewidth=2)
    a1.set_title("Sinal do Wi-Fi na estação (RSSI, mediana móvel de 15 leituras)")
    a1.set_ylabel("dBm")
    a2.plot(leituras["recebido_em"], intervalo_min, color=COR_SERIE, linewidth=0,
            marker="o", markersize=4)
    a2.set_title("Intervalo entre mensagens MQTT recebidas")
    a2.set_ylabel("min")
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(pasta / "comunicacao.png", dpi=150)
    plt.close(fig)


def resumo(leituras, irrigacoes, intervalo_s, pasta):
    ini, fim = leituras["recebido_em"].min(), leituras["recebido_em"].max()
    duracao_s = (fim - ini).total_seconds()
    esperadas = int(duracao_s // intervalo_s) + 1
    recebidas = len(leituras)
    perda = max(0.0, 1 - recebidas / esperadas) * 100

    linhas = [
        f"Período: {ini:%d/%m/%Y %H:%M} a {fim:%d/%m/%Y %H:%M} ({duracao_s / 3600:.1f} h)",
        f"Leituras recebidas por MQTT: {recebidas} de {esperadas} esperadas "
        f"(intervalo {intervalo_s} s), perda de {perda:.1f}%",
        f"Irrigações registradas: {sum(o == 'bomba' for _, o in irrigacoes)} pela bomba, "
        f"{sum(o == 'manual' for _, o in irrigacoes)} manuais",
        f"Leituras do AM2302 com falha (null): {leituras['temp_c'].isna().sum()}",
        "",
        f"{'variável':<22}{'mín':>8}{'média':>8}{'máx':>8}",
    ]
    for col, nome in [("solo_pct", "umidade do solo (%)"), ("solo_bruto", "solo, valor bruto"),
                      ("temp_c", "temperatura (°C)"), ("umid_ar_pct", "umidade do ar (%)"),
                      ("rssi", "RSSI (dBm)")]:
        s = leituras[col].dropna()
        linhas.append(f"{nome:<22}{s.min():>8.1f}{s.mean():>8.1f}{s.max():>8.1f}")

    texto = "\n".join(linhas)
    (pasta / "resumo.txt").write_text(texto + "\n", encoding="utf-8")
    print(texto)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", type=Path, default=COLETA_DIR)
    ap.add_argument("--intervalo", type=int, default=60, help="intervalo de leitura do firmware (s)")
    args = ap.parse_args()

    leituras, irrigacoes = carregar(args.pasta)
    serie_temporal(leituras, irrigacoes, args.pasta)
    comunicacao(leituras, args.pasta)
    resumo(leituras, irrigacoes, args.intervalo, args.pasta)
    print(f"\nGráficos em {args.pasta}")


if __name__ == "__main__":
    main()
