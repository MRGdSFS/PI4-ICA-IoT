"""
Texturas usadas pelos renders da estação SIT (rodar com o Python do sistema, que tem Pillow).

Gera em codes/modelo3d/render/tex/:
  dashboard.png    tela do notebook: UI estilizada "SIT · Dashboard", só barras e curvas genéricas, sem números
  teclado.png      tampo do notebook (teclado e touchpad); o canal alfa é a máscara de metal (1 = alumínio)
  sensor_pcb.png   face do sensor capacitivo de solo (placa preta com serigrafia branca)
  esp32_pcb.png    face de cima da ESP32-S3 DevKit (placa preta)
  protoboard.png   face de cima da protoboard 165x80 (branca, furos de 2,54 mm)

Uso:  python codes/modelo3d/render/texturas.py
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

TEX = Path(__file__).resolve().parent / "tex"
TEX.mkdir(parents=True, exist_ok=True)

FONTES = Path("C:/Windows/Fonts")

# Paleta (docs/v1/especificacao_tecnica.md, seção 8)
AMARELO = "#F5C400"
AMARELO_ESCURO = "#C99700"
TINTA = "#1E1B16"
CREME = "#FBF6E6"
TOMATE = "#D2452C"
FOLHA = "#2E7D32"


def fonte(nome, tamanho):
    for arq in (nome, "segoeui.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(str(FONTES / arq), tamanho)
        except OSError:
            continue
    return ImageFont.load_default()


# ------------------------------------------------------------------
# Dashboard (desenhado em 2x e reduzido, para ter antisserrilhado)
# ------------------------------------------------------------------

def curva_solo(n=400):
    """Dente de serra genérico: o solo seca devagar e sobe de repente a cada rega (sem escala)."""
    t = np.linspace(0, 1, n)
    y = np.zeros(n)
    regas = [0.18, 0.47, 0.78]
    nivel = 0.62
    ultima = 0.0
    for i, ti in enumerate(t):
        if regas and ti >= regas[0]:
            regas.pop(0)
            nivel = 0.86
            ultima = ti
        y[i] = nivel - 0.95 * (ti - ultima) * (1 - 0.3 * (ti - ultima))
    y += 0.004 * np.sin(t * 60) + 0.003 * np.sin(t * 23 + 1)
    return t, np.clip(y, 0.08, 0.95)


def curva_suave(n, fase, amp, base, ondas=1.0, ruido=0.01):
    t = np.linspace(0, 1, n)
    y = base + amp * np.sin(2 * np.pi * (t * ondas) + fase) + ruido * np.sin(t * 70 + fase * 3)
    return t, y


def cartao(d, caixa, raio=26, borda="#E8DFC4"):
    d.rounded_rectangle(caixa, raio, fill="#FFFFFF", outline=borda, width=3)


def plotar_linha(d, caixa, t, y, cor, largura=8, area=None, faixa=None, limiar=None):
    x0, y0, x1, y1 = caixa
    pts = [(x0 + (x1 - x0) * ti, y1 - (y1 - y0) * yi) for ti, yi in zip(t, y)]
    if area:
        d.polygon(pts + [(x1, y1), (x0, y1)], fill=area)
    if faixa:
        fa, fb = faixa
        d.rectangle([x0, y1 - (y1 - y0) * fb, x1, y1 - (y1 - y0) * fa], fill="#E4F0E1")
    # grade recessiva, sem rótulos de valor
    for k in range(1, 4):
        yy = y0 + (y1 - y0) * k / 4
        d.line([(x0, yy), (x1, yy)], fill="#EFE8D4", width=3)
    d.line([(x0, y1), (x1, y1)], fill="#D9CFB2", width=4)
    if limiar is not None:
        yy = y1 - (y1 - y0) * limiar
        for xa in range(int(x0), int(x1), 36):
            d.line([(xa, yy), (min(xa + 18, x1), yy)], fill=TOMATE, width=5)
    d.line(pts, fill=cor, width=largura, joint="curve")


def dashboard(larg=1600, alt=1000, escala=2):
    W, H = larg * escala, alt * escala
    s = escala
    img = Image.new("RGB", (W, H), CREME)
    d = ImageDraw.Draw(img)

    f_titulo = fonte("seguisb.ttf", 40 * s)
    f_cartao = fonte("seguisb.ttf", 23 * s)
    f_menor = fonte("segoeui.ttf", 20 * s)

    # barra superior
    d.rectangle([0, 0, W, 92 * s], fill=TINTA)
    d.rounded_rectangle([34 * s, 20 * s, 86 * s, 72 * s], 12 * s, fill=AMARELO)
    # gota estilizada no logo
    d.ellipse([50 * s, 40 * s, 70 * s, 62 * s], fill=TINTA)
    d.polygon([(60 * s, 28 * s), (51 * s, 47 * s), (69 * s, 47 * s)], fill=TINTA)
    d.text((106 * s, 46 * s), "SIT · Dashboard", font=f_titulo, fill=CREME, anchor="lm")
    d.text((440 * s, 48 * s), "Estação 01 · vaso de tomate", font=f_menor, fill="#BDB49C", anchor="lm")
    # pílulas de status (sem números)
    for i, rot in enumerate(("MQTT", "USB")):
        xa = W - (300 - i * 140) * s
        d.rounded_rectangle([xa, 28 * s, xa + 118 * s, 66 * s], 19 * s, outline="#5C5546", width=2 * s)
        d.ellipse([xa + 16 * s, 40 * s, xa + 30 * s, 54 * s], fill="#57B65C")
        d.text((xa + 42 * s, 47 * s), rot, font=f_menor, fill=CREME, anchor="lm")

    m = 34 * s
    topo = 92 * s + m
    # linha de 4 cartões
    rotulos = ("Umidade do solo", "Temperatura do ar", "Umidade do ar", "Bomba")
    cores = (FOLHA, TOMATE, AMARELO_ESCURO, TINTA)
    niveis = (0.66, 0.48, 0.62, None)
    lc = (W - 5 * m) / 4
    hc = 150 * s
    for i in range(4):
        x0 = m + i * (lc + m)
        cartao(d, [x0, topo, x0 + lc, topo + hc], raio=22 * s)
        d.ellipse([x0 + 26 * s, topo + 28 * s, x0 + 44 * s, topo + 46 * s], fill=cores[i])
        d.text((x0 + 56 * s, topo + 37 * s), rotulos[i], font=f_cartao, fill=TINTA, anchor="lm")
        if niveis[i] is not None:
            # medidor genérico: trilho e preenchimento, sem escala nem valor
            yb = topo + 100 * s
            d.rounded_rectangle([x0 + 26 * s, yb, x0 + lc - 26 * s, yb + 22 * s], 11 * s, fill="#F1EAD5")
            d.rounded_rectangle([x0 + 26 * s, yb, x0 + 26 * s + (lc - 52 * s) * niveis[i], yb + 22 * s],
                                11 * s, fill=cores[i])
        else:
            # chave da bomba e botão "Irrigar" (texto escuro sobre amarelo)
            yb = topo + 84 * s
            d.rounded_rectangle([x0 + 26 * s, yb, x0 + 116 * s, yb + 46 * s], 23 * s, fill="#E3DCC6")
            d.ellipse([x0 + 31 * s, yb + 5 * s, x0 + 67 * s, yb + 41 * s], fill="#FFFFFF")
            d.rounded_rectangle([x0 + 140 * s, yb, x0 + lc - 26 * s, yb + 46 * s], 14 * s, fill=AMARELO)
            d.text(((x0 + 140 * s + x0 + lc - 26 * s) / 2, yb + 23 * s), "Irrigar", font=f_cartao,
                   fill=TINTA, anchor="mm")

    # gráfico grande: umidade do solo (série única, o título nomeia)
    y2 = topo + hc + m
    xg1 = m + 2 * (lc + m) - m
    cartao(d, [m, y2, xg1, H - m], raio=22 * s)
    d.text((m + 28 * s, y2 + 38 * s), "Umidade do solo", font=f_cartao, fill=TINTA, anchor="lm")
    d.text((m + 250 * s, y2 + 39 * s), "faixa ideal e limiar de rega", font=f_menor, fill="#8A8170", anchor="lm")
    t, y = curva_solo()
    plotar_linha(d, [m + 30 * s, y2 + 80 * s, xg1 - 30 * s, H - m - 40 * s], t, y, FOLHA, largura=7 * s,
                 faixa=(0.5, 0.8), limiar=0.4)
    # marcas de rega (gotas) no eixo do tempo
    for tr in (0.18, 0.47, 0.78):
        xx = m + 30 * s + (xg1 - m - 60 * s) * tr
        yy = H - m - 22 * s
        d.ellipse([xx - 9 * s, yy - 6 * s, xx + 9 * s, yy + 12 * s], fill="#3E8FD0")
        d.polygon([(xx, yy - 18 * s), (xx - 8 * s, yy), (xx + 8 * s, yy)], fill="#3E8FD0")

    # coluna direita: dois gráficos pequenos, um por grandeza (sem eixo duplo)
    xd0 = xg1 + m
    hmeio = (H - m - y2 - m) / 2
    for k, (rot, cor, fase) in enumerate((("Temperatura do ar", TOMATE, 0.3), ("Umidade do ar", AMARELO_ESCURO, 2.6))):
        yy0 = y2 + k * (hmeio + m)
        cartao(d, [xd0, yy0, W - m, yy0 + hmeio], raio=22 * s)
        d.text((xd0 + 28 * s, yy0 + 36 * s), rot, font=f_cartao, fill=TINTA, anchor="lm")
        tt, yv = curva_suave(240, fase, 0.22, 0.5, ondas=1.15, ruido=0.012)
        plotar_linha(d, [xd0 + 28 * s, yy0 + 70 * s, W - m - 28 * s, yy0 + hmeio - 26 * s], tt, yv, cor,
                     largura=7 * s)

    img = img.resize((larg, alt), Image.LANCZOS)
    img.save(TEX / "dashboard.png", optimize=True)


# ------------------------------------------------------------------
# Tampo do notebook: 320 x 220 mm a 5 px/mm. v = 1 (topo da imagem) fica do lado da dobradiça.
# ------------------------------------------------------------------

def teclado():
    pxmm = 5
    W, H = 320 * pxmm, 220 * pxmm
    rgb = Image.new("RGB", (W, H), "#565A61")
    alfa = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(rgb)
    da = ImageDraw.Draw(alfa)

    def mm(x, y):  # x local (-160..160), y local (-110 frente .. 110 dobradiça) -> pixel
        return ((x + 160) * pxmm, (110 - y) * pxmm)

    passo = 18.5
    larg_total = 15 * passo
    x_esq = -larg_total / 2
    # poço do teclado
    a, b = mm(x_esq - 3, 97), mm(-x_esq + 3, -12)
    d.rounded_rectangle([a, b], 3 * pxmm, fill="#2B2E33")
    linhas = [
        (93, 10, [1] * 15),
        (80, 15.5, [1] * 13 + [2]),
        (61.5, 15.5, [1.5] + [1] * 12 + [1.5]),
        (43, 15.5, [1.75] + [1] * 11 + [2.25]),
        (24.5, 15.5, [2.25] + [1] * 10 + [2.75]),
        (6, 15.5, [1, 1, 1, 1.25, 5.5, 1.25, 1, 3]),
    ]
    for y_topo, alt_tecla, larguras in linhas:
        x = x_esq
        for i, u in enumerate(larguras):
            w = u * passo - 3
            if y_topo == 6 and i == len(larguras) - 1:
                # setas: meia altura em cima e embaixo
                for j in range(3):
                    xa = x + j * passo
                    for (ya, hh) in ((y_topo, 7), (y_topo - 8.5, 7)):
                        if j != 1 and ya == y_topo:
                            continue
                        p0, p1 = mm(xa, ya), mm(xa + passo - 3, ya - hh)
                        d.rounded_rectangle([p0, p1], 1.2 * pxmm, fill="#141517")
                        da.rounded_rectangle([p0, p1], 1.2 * pxmm, fill=0)
            else:
                p0, p1 = mm(x, y_topo), mm(x + w, y_topo - alt_tecla)
                d.rounded_rectangle([p0, p1], 1.2 * pxmm, fill="#141517")
                da.rounded_rectangle([p0, p1], 1.2 * pxmm, fill=0)
                # leve brilho na borda superior da tecla
                d.line([(p0[0] + 6, p0[1] + 2), (p1[0] - 6, p0[1] + 2)], fill="#2A2C30", width=2)
            x += u * passo
    # touchpad
    p0, p1 = mm(-62, -24), mm(62, -102)
    d.rounded_rectangle([p0, p1], 4 * pxmm, fill="#5E636A", outline="#43474D", width=3)
    rgba = rgb.copy()
    rgba.putalpha(alfa)
    rgba.save(TEX / "teclado.png", optimize=True)


# ------------------------------------------------------------------
# Placa do sensor capacitivo: 23 x 98 mm a 10 px/mm (topo da imagem = ponta do conector)
# ------------------------------------------------------------------

def sensor_pcb():
    px = 10
    W, H = 23 * px, 98 * px
    img = Image.new("RGB", (W, H), "#151515")
    d = ImageDraw.Draw(img)
    branco = "#E8E8E2"
    # área dos componentes
    d.rectangle([1.5 * px, 1.5 * px, W - 1.5 * px, 27 * px], outline=branco, width=3)
    # linha de profundidade máxima de inserção
    d.line([(1 * px, 33 * px), (W - 1 * px, 33 * px)], fill=branco, width=4)
    f = fonte("segoeuib.ttf", 26)
    d.text((W / 2, 30 * px), "v2.0", font=f, fill=branco, anchor="mm")
    # contornos de componentes
    for (x0, y0, x1, y1) in ((5, 8, 18, 15), (4, 18, 9, 22), (13, 18, 19, 22), (8, 23, 15, 26)):
        d.rectangle([x0 * px, y0 * px, x1 * px, y1 * px], outline=branco, width=2)
    # trilha de cobre escurecida (sob a máscara) na área sensora
    d.rounded_rectangle([5 * px, 40 * px, W - 5 * px, 92 * px], 4 * px, outline="#262626", width=6)
    img.save(TEX / "sensor_pcb.png", optimize=True)


# ------------------------------------------------------------------
# ESP32-S3 DevKit: 69 x 26 mm a 12 px/mm. Esquerda da imagem = ponta da USB.
# ------------------------------------------------------------------

def esp32_pcb():
    px = 12
    W, H = 69 * px, 26 * px
    img = Image.new("RGB", (W, H), "#141414")
    d = ImageDraw.Draw(img)
    branco = "#DADAD4"
    # furos dos pinos (2 fileiras de 22) com anel dourado
    for fila in (1.6, 24.4):
        for i in range(22):
            cx, cy = (6.5 + i * 2.54) * px, fila * px
            d.ellipse([cx - 0.85 * px, cy - 0.85 * px, cx + 0.85 * px, cy + 0.85 * px], fill="#B8954A")
            d.ellipse([cx - 0.45 * px, cy - 0.45 * px, cx + 0.45 * px, cy + 0.45 * px], fill="#2A2A2A")
            # rótulo de pino (traço de serigrafia, ilegível de propósito)
            yy = cy + (2.0 if fila < 10 else -2.0) * px
            d.line([(cx - 0.6 * px, yy), (cx + 0.6 * px, yy)], fill=branco, width=3)
    f = fonte("segoeuib.ttf", 34)
    d.text((24 * px, 13 * px), "ESP32-S3", font=f, fill=branco, anchor="mm")
    d.rectangle([13 * px, 9.5 * px, 35 * px, 16.5 * px], outline=branco, width=2)
    img.save(TEX / "esp32_pcb.png", optimize=True)


# ------------------------------------------------------------------
# Protoboard 165 x 80 mm a 10 px/mm (duas protoboards de 830 pontos lado a lado)
# ------------------------------------------------------------------

def protoboard():
    px = 10
    W, H = 165 * px, 80 * px
    img = Image.new("RGB", (W, H), "#F3F2EC")
    d = ImageDraw.Draw(img)
    passo = 2.54
    furo = 0.55 * px
    ncol = 62
    x0 = (165 - (ncol - 1) * passo) / 2

    def furos(y_mm, grupos_de_5=False):
        for c in range(ncol):
            if grupos_de_5 and c % 6 == 5:
                continue
            cx, cy = (x0 + c * passo) * px, y_mm * px
            d.rectangle([cx - furo, cy - furo, cx + furo, cy + furo], fill="#3A3A3A")

    y = 3.2
    blocos = []
    for metade in range(2):
        # par de trilhos de alimentação com linhas vermelha e azul
        d.line([(6 * px, (y - 1.7) * px), ((165 - 6) * px, (y - 1.7) * px)], fill="#D23A2E", width=4)
        furos(y, True)
        furos(y + passo, True)
        d.line([(6 * px, (y + passo + 1.7) * px), ((165 - 6) * px, (y + passo + 1.7) * px)], fill="#2F5FC4", width=4)
        y += 2 * passo + 3.4
        for bloco in range(2):
            for k in range(5):
                furos(y + k * passo)
            blocos.append(y)
            y += 5 * passo
            if bloco == 0:
                # canal central
                d.rectangle([2 * px, (y + 0.3) * px, (165 - 2) * px, (y + 2.2) * px], fill="#E2E0D8")
                y += 2.5
        y += 3.4
    img.save(TEX / "protoboard.png", optimize=True)


if __name__ == "__main__":
    dashboard()
    teclado()
    sensor_pcb()
    esp32_pcb()
    protoboard()
    for p in sorted(TEX.glob("*.png")):
        print(p.name, Image.open(p).size, f"{p.stat().st_size // 1024} KB")
