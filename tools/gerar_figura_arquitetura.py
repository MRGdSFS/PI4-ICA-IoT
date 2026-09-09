"""Gera a Figura 1 (arquitetura do SIT) em PNG e SVG.

Fonte única da figura usada no README, no documento da entrega v0 e no
Google Docs. Para regerar:

    python tools/gerar_figura_arquitetura.py

Saída: docs/entregas/v0-descricao-da-aplicacao/figuras/arquitetura-sit.{png,svg}
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

W, H = 1160, 900
OUT = Path(__file__).resolve().parents[1] / "docs/entregas/v0-descricao-da-aplicacao/figuras"

INK = "#0f172a"
BODY = "#1e293b"
MUTED = "#64748b"
LINE = "#334155"

X0, X1 = -40, W + 130       # margem para os laços de retorno
Y1 = H + 30
# figsize casa 1 unidade de dado = 1 px, para o texto nunca estourar as caixas
fig, ax = plt.subplots(figsize=((X1 - X0) / 100, Y1 / 100), dpi=100)
ax.set_xlim(X0, X1)
ax.set_ylim(Y1, 0)          # y cresce para baixo
ax.axis("off")
fig.patch.set_facecolor("white")


def box(x, y, w, h, *, fill, edge, lw=2.0, dashed=False, radius=9):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=fill, edgecolor=edge, linewidth=lw,
        linestyle=(0, (5, 4)) if dashed else "solid",
        mutation_aspect=1, zorder=1,
    )
    ax.add_patch(p)


def txt(x, y, s, *, size=12, color=BODY, weight="normal", ha="left", rot=0):
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
            ha=ha, va="center", rotation=rot, zorder=3,
            family=["Segoe UI", "DejaVu Sans", "Arial"])


def arrow(x1, y1, x2, y2, *, color=LINE, lw=2.0, head=True):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>" if head else "-",
        mutation_scale=16, color=color, linewidth=lw,
        shrinkA=0, shrinkB=0, zorder=2,
    ))


def polyline(pts, *, color=LINE, lw=2.0, head=True):
    for i in range(len(pts) - 1):
        last = i == len(pts) - 2
        arrow(*pts[i], *pts[i + 1], color=color, lw=lw, head=head and last)


# ------------------------------------------------------------------ título
txt(W / 2, 30, "SIT — Sistema IoT de Irrigação Inteligente para Cultivo de Tomate",
    size=17, weight="bold", color=INK, ha="center")
txt(W / 2, 56, "Figura 1 — Arquitetura geral do sistema (preliminar)",
    size=11.5, color=MUTED, ha="center")

# ------------------------------------------- 1. percepção e atuação
box(30, 76, 1100, 198, fill="#f8fafc", edge="#cbd5e1", lw=1.4, dashed=True)
txt(48, 94, "1 · CAMADA DE PERCEPÇÃO E ATUAÇÃO", size=10, weight="bold", color="#475569")

box(60, 110, 480, 150, fill="#eff6ff", edge="#2563eb")
txt(82, 133, "Nó de campo — ESP32 (WROOM-32)", size=13.5, weight="bold", color="#1e3a8a")
txt(82, 158, "Umidade e temperatura do solo · BME280", size=11.5)
txt(82, 178, "(T / UR / pressão do ar) · sensor de vazão", size=11.5)
txt(82, 202, "Atuação: driver / relé → bomba de irrigação", size=11.5)
txt(82, 226, "Decisão LOCAL + intertravamentos de segurança", size=11.5,
    weight="bold", color="#b91c1c")
txt(82, 247, "irriga mesmo sem rede · buffer local de telemetria", size=10.5, color=MUTED)

box(620, 110, 480, 150, fill="#faf5ff", edge="#7e22ce")
txt(642, 133, "Sensor virtual (Python)", size=13.5, weight="bold", color="#581c87")
txt(642, 158, "Replay do dataset real de cultivo de tomate", size=11.5)
txt(642, 178, "(testbed 2023–2025, amostragem de 10 min)", size=11.5)
txt(642, 202, "Aceleração temporal configurável", size=11.5)
txt(642, 226, "Injeção de ruído, atraso e perda de amostras", size=11.5,
    weight="bold", color="#7e22ce")
txt(642, 247, "testa o sistema completo antes do hardware existir", size=10.5, color=MUTED)

txt(W / 2, 286, "mesmo contrato de mensagens — tópicos MQTT e payload JSON idênticos",
    size=11.5, weight="bold", color=LINE, ha="center")
polyline([(200, 262), (200, 312), (580, 312)], head=False)
polyline([(960, 262), (960, 312), (580, 312)], head=False)
arrow(580, 312, 580, 330)

# ------------------------------------------------ 2. comunicação
box(30, 332, 1100, 74, fill="#ecfeff", edge="#0e7490")
txt(48, 350, "2 · CAMADA DE COMUNICAÇÃO", size=10, weight="bold", color="#155e75")
txt(W / 2, 375, "Wi-Fi 802.11 b/g/n   +   MQTT   —   Broker Mosquitto",
    size=13.5, weight="bold", color=INK, ha="center")
txt(W / 2, 394, "autenticação · ACL por tópico · QoS 1 nos comandos · TLS previsto",
    size=11, color=LINE, ha="center")
arrow(580, 406, 580, 438)

# --------------------------------------------- 3. borda / névoa
box(30, 442, 1100, 168, fill="#f0fdf4", edge="#15803d")
txt(48, 460, "3 · CAMADA DE BORDA / NÉVOA   (computador local ou single-board)",
    size=10, weight="bold", color="#166534")

box(62, 482, 292, 106, fill="white", edge="#86efac", lw=1.4)
txt(208, 506, "Ingestão", size=13, weight="bold", color="#14532d", ha="center")
txt(208, 530, "assinante MQTT", size=11, ha="center")
txt(208, 550, "validação e controle de", size=11, ha="center")
txt(208, 570, "qualidade das amostras", size=11, ha="center")

box(374, 482, 292, 106, fill="white", edge="#86efac", lw=1.4)
txt(520, 506, "Armazenamento", size=13, weight="bold", color="#14532d", ha="center")
txt(520, 530, "banco de séries temporais", size=11, ha="center")
txt(520, 550, "telemetria · eventos de", size=11, ha="center")
txt(520, 570, "irrigação · falhas", size=11, ha="center")

box(686, 482, 412, 106, fill="white", edge="#15803d")
txt(892, 506, "Motor de decisão", size=13, weight="bold", color="#14532d", ha="center")
txt(892, 530, "baseline por limiar fixo   |   modelo de IC", size=11, ha="center")
txt(892, 550, "decide SE irriga e QUANTO irrigar", size=11, ha="center")
txt(892, 570, "publica o comando de atuação", size=11, ha="center")

arrow(354, 535, 372, 535)
arrow(666, 535, 684, 535)

txt(W / 2, 632, "ciclo fechado:  medir → decidir → atuar → medir o resultado da própria decisão",
    size=11.5, weight="bold", color=LINE, ha="center")

# ------------------------------------------------ 4. aplicação
arrow(150, 612, 150, 654)
arrow(1010, 612, 1010, 654)

box(30, 656, 1100, 186, fill="#fffbeb", edge="#b45309")
txt(48, 674, "4 · CAMADA DE APLICAÇÃO E ANÁLISE", size=10, weight="bold", color="#92400e")

box(62, 694, 478, 130, fill="white", edge="#fbbf24", lw=1.4)
txt(301, 718, "Painel de monitoramento", size=13, weight="bold", color="#92400e", ha="center")
txt(301, 742, "séries temporais · estado da bomba · eventos", size=11, ha="center")
txt(301, 762, "volume de água acumulado por estratégia", size=11, ha="center")
txt(301, 782, "modo de operação e comando manual", size=11, ha="center")
txt(301, 802, "explicação da decisão automática", size=11, ha="center")

box(620, 694, 478, 130, fill="white", edge="#fbbf24", lw=1.4)
txt(859, 718, "Laboratório de IC (offline)", size=13, weight="bold", color="#92400e", ha="center")
txt(859, 742, "exploração e preparação dos dados", size=11, ha="center")
txt(859, 762, "treino · validação temporal · análise de erros", size=11, ha="center")
txt(859, 782, "seleção sob restrição de memória e latência", size=11, ha="center")
txt(859, 802, "exportação do modelo para a borda", size=11, ha="center")

# --------------------------------------------- laços de retorno
polyline([(1098, 535), (1200, 535), (1200, 185), (1102, 185)],
         color="#c2410c", lw=2.4)
txt(1222, 360, "comando de atuação (bomba)", size=10.5, weight="bold",
    color="#c2410c", ha="center", rot=90)

polyline([(859, 824), (859, 872), (-22, 872), (-22, 185), (58, 185)],
         color="#15803d", lw=2.4)
txt(420, 860, "modelo embarcado no nó de borda (TinyML)", size=10.5,
    weight="bold", color="#15803d", ha="center")

OUT.mkdir(parents=True, exist_ok=True)
for ext in ("png", "svg"):
    fig.savefig(OUT / f"arquitetura-sit.{ext}", dpi=200 if ext == "png" else None,
                bbox_inches="tight", facecolor="white", pad_inches=0.12)
    print("gerado:", (OUT / f"arquitetura-sit.{ext}").as_posix())
