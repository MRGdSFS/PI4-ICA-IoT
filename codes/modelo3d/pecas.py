"""
Peças impressas da estação SIT (paramétrico, medidas em mm).

Gera cinco STL em outputs/modelo3d/:
  caixa_base.stl   caixa da eletrônica (protoboard com ESP32, transistor, resistor e diodo)
  caixa_tampa.stl  tampa com ventilação e rasgos de abraçadeira para o AM2302
  coroa_vaso.stl   anel que encaixa na boca do vaso, guia a mangueira e passa o cabo do sensor
  reservatorio.stl        reservatório da bomba, encaixa na lateral da caixa por dois rabos de andorinha
  reservatorio_tampa.stl  tampa do reservatório com boca de abastecimento e saída da mangueira e do cabo

Todas imprimem sem suporte na orientação em que saem (a tampa sai com a aba para cima,
a coroa sai com o apoio para baixo; vire as duas na montagem).

Uso:
  pip install manifold3d trimesh
  python codes/modelo3d/pecas.py

Medidas marcadas com MEDIR são estimativas de catálogo: confira com régua antes de imprimir.
"""

from functools import reduce
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold

# ============================================================
# MEDIDAS
# ============================================================

# Componentes
PROTOBOARD = (165, 80)        # medido
DHT = (59, 27)                # AM2302 com cabo (caixinha branca), MEDIR
VASO_DIAMETRO = 100           # diâmetro externo da boca do vaso, medido
MANGUEIRA_EXTERNO = 5.0       # diâmetro externo da mangueira, medido

# Impressão
PAREDE = 2.4
FUNDO = 2.0
FOLGA = 2.0                   # sobra em volta das placas
ALTURA_INTERNA = 40           # protoboard (~10) + ESP32 com pinos (~15) + jumpers
SEGMENTOS = 128

# Rasgos de cabo
# Reservatório (lado y=0 da caixa); ~540 mL com as medidas abaixo
RES_INTERNO_Y = 80
RES_PAREDE_ENCAIXE = 6.0      # parede grossa onde entram os rabos de andorinha
RABO = (8.0, 12.0, 4.0)       # largura na raiz, largura na ponta, profundidade
RABO_JOGO = 0.25              # folga por lado no encaixe; aumente se ficar duro

USB_LARGURA = 16              # rasgo da USB, na ponta da protoboard onde fica a ESP32
CABO_LARGURA = 8              # rasgos do sensor de solo, bomba e reserva
CABO_PROFUNDIDADE = 14

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "modelo3d"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================


def caixa(x, y, z, origem=(0, 0, 0)):
    return Manifold.cube((x, y, z)).translate(origem)


def cilindro(h, r, origem=(0, 0, 0)):
    return Manifold.cylinder(h, r, r, SEGMENTOS).translate(origem)


def uniao(pecas):
    return reduce(lambda a, b: a + b, pecas)


# Interior: protoboard ao longo de X; o driver da bomba (transistor, resistor, diodo) vai na própria protoboard
INT_X = PROTOBOARD[0] + 2 * FOLGA
INT_Y = PROTOBOARD[1] + 2 * FOLGA
EXT_X = INT_X + 2 * PAREDE
EXT_Y = INT_Y + 2 * PAREDE
EXT_Z = FUNDO + ALTURA_INTERNA

Y_PROTO_CENTRO = PAREDE + FOLGA + PROTOBOARD[1] / 2


def caixa_base():
    corpo = caixa(EXT_X, EXT_Y, EXT_Z) - caixa(INT_X, INT_Y, ALTURA_INTERNA + 1, (PAREDE, PAREDE, FUNDO))

    # rasgos abertos por cima: USB na ponta x=0, três cabos na ponta oposta
    topo = EXT_Z - CABO_PROFUNDIDADE
    usb = caixa(PAREDE + 2, USB_LARGURA, EXT_Z, (-1, Y_PROTO_CENTRO - USB_LARGURA / 2, FUNDO + 10))
    cabos = uniao([
        caixa(PAREDE + 2, CABO_LARGURA, CABO_PROFUNDIDADE + 1, (EXT_X - PAREDE - 1, y, topo))
        for y in np.linspace(EXT_Y * 0.2, EXT_Y * 0.8, 3) - CABO_LARGURA / 2
    ])

    return corpo + rabos_de_andorinha() - usb - cabos


X_RABOS = (EXT_X * 0.25, EXT_X * 0.75)


def trapezio(raiz, ponta, profundidade, altura, x_centro, sentido):
    """Prisma vertical com seção de rabo de andorinha; a raiz fica em y=0, a ponta em y=sentido*profundidade."""
    pontos = [(x_centro - raiz / 2, 0), (x_centro + raiz / 2, 0),
              (x_centro + ponta / 2, sentido * profundidade), (x_centro - ponta / 2, sentido * profundidade)]
    if sentido < 0:
        pontos.reverse()
    return CrossSection([pontos]).extrude(altura)


def rabos_de_andorinha():
    raiz, ponta, prof = RABO
    return uniao([trapezio(raiz, ponta, prof, EXT_Z, x, -1) for x in X_RABOS])


RES_EXT_Y = RES_INTERNO_Y + PAREDE + RES_PAREDE_ENCAIXE


def reservatorio():
    corpo = caixa(EXT_X, RES_EXT_Y, EXT_Z) - caixa(INT_X, RES_INTERNO_Y, ALTURA_INTERNA + 1, (PAREDE, PAREDE, FUNDO))

    # encaixes fêmea na face que encosta na caixa (y = RES_EXT_Y), com folga, passando de ponta a ponta
    raiz, ponta, prof = RABO
    encaixes = uniao([
        trapezio(raiz + 2 * RABO_JOGO, ponta + 2 * RABO_JOGO, prof + RABO_JOGO, EXT_Z + 2, x, -1)
        .translate((0, RES_EXT_Y + 0.01, -1))
        for x in X_RABOS
    ])
    return corpo - encaixes


def reservatorio_tampa():
    espessura = 2.0
    aba_altura = 4.0
    aba_parede = 1.5
    jogo = 0.3

    placa = caixa(EXT_X, RES_EXT_Y, espessura)
    ax, ay = INT_X - 2 * jogo, RES_INTERNO_Y - 2 * jogo
    aba = caixa(ax, ay, aba_altura) - caixa(ax - 2 * aba_parede, ay - 2 * aba_parede, aba_altura + 1,
                                             (aba_parede, aba_parede, -0.5))
    aba = aba.translate((PAREDE + jogo, PAREDE + jogo, espessura))

    y_meio = PAREDE + RES_INTERNO_Y / 2
    boca = cilindro(espessura + 2, 15, (EXT_X * 0.3, y_meio, -1))
    # mangueira e cabo da bomba saem pela ponta dos rasgos de cabo da caixa
    saida = caixa(12, 22, espessura + 2, (EXT_X - PAREDE - 20, y_meio - 11, -1))
    return placa + aba - boca - saida


def caixa_tampa():
    espessura = 2.0
    aba_altura = 4.0
    aba_parede = 1.5
    jogo = 0.3

    placa = caixa(EXT_X, EXT_Y, espessura)

    # aba que entra na caixa (sai para cima na impressão)
    ax, ay = INT_X - 2 * jogo, INT_Y - 2 * jogo
    aba = caixa(ax, ay, aba_altura) - caixa(ax - 2 * aba_parede, ay - 2 * aba_parede, aba_altura + 1,
                                             (aba_parede, aba_parede, -0.5))
    aba = aba.translate((PAREDE + jogo, PAREDE + jogo, espessura))

    # a aba não pode tampar os rasgos de cabo
    vaos = uniao([
        caixa(8, USB_LARGURA + 2, aba_altura + 1, (0, Y_PROTO_CENTRO - USB_LARGURA / 2 - 1, espessura)),
        caixa(8, EXT_Y, aba_altura + 1, (EXT_X - 8, 0, espessura)),
    ])
    aba = aba - vaos

    # ventilação na metade da tampa oposta ao AM2302
    ventilacao = uniao([
        caixa(30, 3, espessura + 2, (x, y, -1))
        for x in (EXT_X * 0.5, EXT_X * 0.72)
        for y in np.arange(EXT_Y * 0.2, EXT_Y * 0.8, 7)
    ])

    # AM2302 por cima da tampa, longe do calor de dentro: dois rasgos de abraçadeira + furo do cabo
    x_dht = EXT_X * 0.05 + 4
    y_dht = EXT_Y / 2 - DHT[1] / 2
    abracadeiras = uniao([
        caixa(3, DHT[1] + 8, espessura + 2, (x_dht + dx, y_dht - 4, -1))
        for dx in (8, DHT[0] - 14)
    ])
    furo_cabo = cilindro(espessura + 2, 3.5, (x_dht + DHT[0] + 6, EXT_Y / 2, -1))

    return placa + aba - ventilacao - abracadeiras - furo_cabo


def coroa_vaso():
    r_int = VASO_DIAMETRO / 2 + 0.75
    r_ext = r_int + PAREDE
    apoio = 2.0             # anel que fica em cima da borda do vaso
    apoio_largura = 4.0
    altura = 15.0

    anel = cilindro(altura, r_ext) - cilindro(altura + 2, r_int, (0, 0, -1))
    flange = cilindro(apoio, r_ext) - cilindro(apoio + 2, r_int - apoio_largura, (0, 0, -1))

    # braço com guia da mangueira, apontando para o centro do vaso
    r_furo = MANGUEIRA_EXTERNO / 2 + 0.25
    x_furo = r_int - apoio_largura - 9
    braco = caixa(14, 16, apoio, (x_furo - 4, -8, 0))
    guia = cilindro(12, r_furo + 2.4, (x_furo, 0, 0))
    furo = cilindro(14, r_furo, (x_furo, 0, -1))

    # passagem do cabo do sensor de solo por cima da borda, do outro lado
    passagem = caixa(r_ext - r_int + apoio_largura + 2, CABO_LARGURA, 6,
                     (-(r_ext + 1), -CABO_LARGURA / 2, -1))

    return anel + flange + braco + guia - furo - passagem


def salvar(manifold, nome):
    malha = manifold.to_mesh()
    tm = trimesh.Trimesh(vertices=np.asarray(malha.vert_properties)[:, :3],
                         faces=np.asarray(malha.tri_verts))
    caminho = OUTPUT_DIR / f"{nome}.stl"
    tm.export(caminho)
    dx, dy, dz = tm.extents
    print(f"{caminho.name}: {dx:.1f} x {dy:.1f} x {dz:.1f} mm, estanque={tm.is_watertight}")
    return tm


if __name__ == "__main__":
    salvar(caixa_base(), "caixa_base")
    salvar(caixa_tampa(), "caixa_tampa")
    salvar(coroa_vaso(), "coroa_vaso")
    salvar(reservatorio(), "reservatorio")
    salvar(reservatorio_tampa(), "reservatorio_tampa")
