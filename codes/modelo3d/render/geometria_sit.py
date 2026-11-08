"""
Geometria da estação SIT montada (só numpy), usada pelo renderizador render_sit.py.

Peças impressas lidas dos STL de outputs/modelo3d/ (não altera pecas.py nem os STL).
Montagem (mm, origem no canto da caixa), conforme docs/v1/especificacao_tecnica.md seção 3:
  caixa_base    como sai do STL: x 0..173,8  y 0..88,8  z 0..42
  caixa_tampa   virada 180° em torno de X: placa em z 42..44, aba para dentro da caixa
  reservatorio  y -88,4..0, encaixado pelos rabos de andorinha na face y=0
  coroa_vaso    virada 180° em torno de X: lábio interno apoiado na borda do vaso (z=80)
Componentes (vaso, terra, sensor, bomba, água, mangueira, AM2302, ESP32, notebook) são modelos simplificados.
"""

import math
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
STL = RAIZ / "outputs" / "modelo3d"

# Medidas das peças (iguais às do pecas.py)
EXT_X, EXT_Y, EXT_Z = 173.8, 88.8, 42.0
RES_EXT_Y = 88.4
Y_MEIO = 44.4
X_DHT = EXT_X * 0.05 + 4  # 12,69
Y_CABOS = (EXT_Y * 0.2, EXT_Y * 0.5, EXT_Y * 0.8)  # 17,76 / 44,4 / 71,04
COROA_X_FURO = 50.75 - 4 - 9  # 37,75 (guia da mangueira, no referencial da coroa)

# Vaso: 100 mm de diâmetro na boca, 80 mm de altura
VASO_H = 80.0
TERRA_Z = 65.0

# Layout padrão (mesa): estação na origem, vaso à direita, notebook à esquerda e atrás
VASO_C = (258.0, -14.0)
ANG_GUIA = -math.pi / 2  # guia da mangueira virada para a frente (-y); rasgo do cabo para trás (+y)
NOTEBOOK_MESA = dict(centro=(-300, 150), yaw_graus=22, aberto=True)


def r_interno_vaso(z):
    return 32.8 + 0.1706 * z


_TAB = np.random.default_rng(7).random((256, 256)) * 2 - 1


def ruido2(x, y):
    """Ruído de valor 2D em [-1, 1] (interpolação suave)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - xi, y - yi
    u, v = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = _TAB[xi & 255, yi & 255]
    b = _TAB[(xi + 1) & 255, yi & 255]
    c = _TAB[xi & 255, (yi + 1) & 255]
    d = _TAB[(xi + 1) & 255, (yi + 1) & 255]
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v


def fbm2(x, y, oitavas=4):
    tot, amp, norma = 0.0, 1.0, 0.0
    for k in range(oitavas):
        tot = tot + amp * ruido2(x * 2 ** k + 17.3 * k, y * 2 ** k - 9.1 * k)
        norma += amp
        amp *= 0.5
    return tot / norma


class Cena:
    """Lista de malhas (V em mm, faces, material, suavização por ângulo, função de UV)."""

    def __init__(self):
        self.malhas = []
        self.rotulos = {}

    def add(self, nome, VF, mat, desloc=(0, 0, 0), suave=None, uv=None, bevel=None):
        V, F = VF
        m = dict(nome=nome, V=transf(V, None, desloc), F=[list(map(int, f)) for f in F], mat=mat,
                 suave=suave, uv=uv)
        self.malhas.append(m)
        return m


# ======================================================================
# Utilidades de malha (numpy, em mm)
# ======================================================================

def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def transf(V, R=None, t=(0, 0, 0)):
    V = np.asarray(V, float)
    if R is not None:
        V = V @ np.asarray(R).T
    return V + np.asarray(t, float)


def juntar(partes):
    Vs, Fs, n = [], [], 0
    for V, F in partes:
        Vs.append(np.asarray(V, float))
        Fs.extend([[i + n for i in f] for f in F])
        n += len(V)
    return np.vstack(Vs), Fs


def caixa_np(x0, y0, z0, x1, y1, z1):
    V = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
         [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]
    F = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return np.array(V, float), F


def prisma_np(poly, z0, z1):
    """Prisma vertical a partir de um polígono 2D (anti-horário)."""
    poly = np.asarray(poly, float)
    n = len(poly)
    V = np.vstack([np.c_[poly, np.full(n, z0)], np.c_[poly, np.full(n, z1)]])
    F = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]
    F += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    return V, F


def ret_arred(w, h, r, n=8, cx=0.0, cy=0.0):
    pts = []
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + sx * (w / 2 - r), cy + sy * (h / 2 - r)
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts


def cilindro_np(r, z0, z1, n=48, cx=0.0, cy=0.0):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    anel = np.c_[cx + r * np.cos(a), cy + r * np.sin(a)]
    return prisma_np(anel, z0, z1)


def cilindro_eixo(p0, p1, r, n=32):
    """Cilindro entre dois pontos quaisquer."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    eixo = p1 - p0
    L = np.linalg.norm(eixo)
    V, F = cilindro_np(r, 0, L, n)
    z = eixo / L
    x = np.cross(z, [0, 0, 1.0]) if abs(z[2]) < 0.9 else np.cross(z, [1.0, 0, 0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.c_[x, y, z]
    return transf(V, R, p0), F


def revolucao_np(perfil, n=128):
    """Superfície de revolução em torno de z. perfil: lista de (r, z); r = 0 vira polo."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    V, aneis = [], []
    for r, z in perfil:
        if r < 1e-9:
            aneis.append([len(V)])
            V.append([0, 0, z])
        else:
            idx = list(range(len(V), len(V) + n))
            V.extend(np.c_[r * np.cos(a), r * np.sin(a), np.full(n, z)].tolist())
            aneis.append(idx)
    F = []
    for A, B in zip(aneis[:-1], aneis[1:]):
        if len(A) == 1 and len(B) == 1:
            continue
        if len(A) == 1:
            F += [[A[0], B[i], B[(i + 1) % n]] for i in range(n)]
        elif len(B) == 1:
            F += [[A[i], B[0], A[(i + 1) % n]] for i in range(n)]
        else:
            F += [[A[i], B[i], B[(i + 1) % n], A[(i + 1) % n]] for i in range(n)]
    return np.array(V, float), F


def spline(pontos, passo=1.0):
    """Catmull-Rom centrípeta reamostrada por comprimento de arco."""
    P = np.asarray(pontos, float)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(len(P) - 3):
        p0, p1, p2, p3 = P[i:i + 4]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** 0.5
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** 0.5
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** 0.5
        for t in np.linspace(t1, t2, 24, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(P[-2])
    C = np.array(out)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
    n = max(int(d[-1] / passo), 2)
    s = np.linspace(0, d[-1], n + 1)
    return np.c_[[np.interp(s, d, C[:, k]) for k in range(3)]].T


def quadros(C):
    T = np.gradient(C, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    ref = np.array([0, 0, 1.0]) if abs(T[0, 2]) < 0.9 else np.array([1.0, 0, 0])
    N = [np.cross(T[0], ref)]
    N[0] /= np.linalg.norm(N[0])
    for i in range(1, len(C)):
        v = N[-1] - np.dot(N[-1], T[i]) * T[i]
        N.append(v / np.linalg.norm(v))
    N = np.array(N)
    B = np.cross(T, N)
    return T, N, B


def tubo_np(pontos, r, n=16, r_int=None, passo=1.0, C=None, quadro=None):
    if C is None:
        C = spline(pontos, passo)
    T, N, B = quadro if quadro is not None else quadros(C)
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    m = len(C)

    def aneis(raio):
        return (C[:, None, :] + raio * (np.cos(a)[None, :, None] * N[:, None, :] +
                                        np.sin(a)[None, :, None] * B[:, None, :])).reshape(-1, 3)

    def lateral(base, inverter=False):
        F = []
        for i in range(m - 1):
            for j in range(n):
                q = [base + i * n + j, base + i * n + (j + 1) % n, base + (i + 1) * n + (j + 1) % n,
                     base + (i + 1) * n + j]
                F.append(q[::-1] if inverter else q)
        return F

    if r_int is None:
        V = aneis(r)
        F = lateral(0)
        F.append(list(range(n - 1, -1, -1)))
        F.append([(m - 1) * n + j for j in range(n)])
        return V, F
    V = np.vstack([aneis(r), aneis(r_int)])
    F = lateral(0) + lateral(m * n, inverter=True)
    k = m * n
    for j in range(n):
        j2 = (j + 1) % n
        F.append([j2, j, k + j, k + j2])
        e, ei = (m - 1) * n, k + (m - 1) * n
        F.append([e + j, e + j2, ei + j2, ei + j])
    return V, F


def fita_np(pontos, largura, espessura, eixo_largura, passo=0.6):
    """Fita de seção retangular (abraçadeira); a largura fica ao longo de eixo_largura."""
    C = spline(pontos, passo)
    T = np.gradient(C, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    W = np.asarray(eixo_largura, float)
    N = np.cross(W, T)
    N /= np.linalg.norm(N, axis=1)[:, None]
    cantos = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    V = np.vstack([C + sw * largura / 2 * W + sn * espessura / 2 * N for (sw, sn) in cantos])
    m = len(C)
    V = V.reshape(4, m, 3).transpose(1, 0, 2).reshape(-1, 3)
    F = []
    for i in range(m - 1):
        for j in range(4):
            j2 = (j + 1) % 4
            F.append([i * 4 + j, i * 4 + j2, (i + 1) * 4 + j2, (i + 1) * 4 + j])
    F.append([3, 2, 1, 0])
    F.append([(m - 1) * 4 + j for j in range(4)])
    return V, F


def ler_stl(nome):
    dados = (STL / f"{nome}.stl").read_bytes()
    n = int.from_bytes(dados[80:84], "little")
    tipo = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec = np.frombuffer(dados, dtype=tipo, count=n, offset=84)
    v = rec["v"].reshape(-1, 3).astype(float)
    uniq, inv = np.unique(np.round(v, 4), axis=0, return_inverse=True)
    F = inv.reshape(-1, 3)
    ok = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])
    return uniq, F[ok].tolist()


def pecas_impressas(c, d=(0, 0, 0), tampa=True, dz_tampa=0.0, dz_res=0.0):
    V, F = ler_stl("caixa_base")
    c.add("caixa_base", (V, F), "petg", d, bevel=0.45)
    if tampa:
        V, F = ler_stl("caixa_tampa")
        V = transf(V, rot_x(math.pi), (0, EXT_Y, EXT_Z + 2 + dz_tampa))
        c.add("caixa_tampa", (V, F), "petg", d, bevel=0.45)
    V, F = ler_stl("reservatorio")
    c.add("reservatorio", (transf(V, None, (0, -RES_EXT_Y, dz_res)), F), "petg", d, bevel=0.45)


def coroa_e_vaso(c, centro, ang_guia, dz_coroa=0.0, sensor=True):
    """Vaso de terracota com terra e a coroa virada por cima. ang_guia: direção da guia (rad)."""
    cx, cy = centro
    # vaso (perfil de revolução)
    perfil = [(0, 0), (34.5, 0), (36, 1.5), (47.6, 68), (50, 68), (50, 80), (r_interno_vaso(80), 80),
              (r_interno_vaso(4), 4), (0, 4)]
    V, F = revolucao_np(perfil, 128)
    c.add("vaso", (V, F), "terracota", (cx, cy, 0), suave=35)
    # terra: disco com relevo
    R = r_interno_vaso(TERRA_Z) + 0.6
    nr, na = 48, 160
    pts, faces = [[0, 0, 0]], []
    for i in range(1, nr + 1):
        r = R * i / nr
        for j in range(na):
            a = 2 * math.pi * j / na
            pts.append([r * math.cos(a), r * math.sin(a), 0])
    pts = np.array(pts)
    for j in range(na):
        faces.append([0, 1 + j, 1 + (j + 1) % na])
    for i in range(1, nr):
        b0, b1 = 1 + (i - 1) * na, 1 + i * na
        for j in range(na):
            faces.append([b0 + j, b1 + j, b1 + (j + 1) % na, b0 + (j + 1) % na])
    x, y = pts[:, 0], pts[:, 1]
    h = (1.1 * ruido2(x * 0.09 + 3.1, y * 0.09) + 0.5 * ruido2(x * 0.25, y * 0.25 + 7.7)
         + 0.25 * ruido2(x * 0.6 + 1.3, y * 0.6))
    rr = np.hypot(x, y)
    h += 1.4 * np.maximum(0.0, (rr - (R - 6)) / 6) ** 2  # sobe junto da parede
    pts[:, 2] = h
    c.add("terra", (pts, faces), "terra", (cx, cy, TERRA_Z), suave=80)
    # coroa virada (lábio em cima, apoiado na borda z=80), girada para a guia apontar em ang_guia
    V, F = ler_stl("coroa_vaso")
    V = transf(V, rot_x(math.pi), (0, 0, 82 + dz_coroa))
    V = transf(V, rot_z(ang_guia), (cx, cy, 0))
    c.add("coroa_vaso", (V, F), "petg", suave=35)
    guia = (cx + COROA_X_FURO * math.cos(ang_guia), cy + COROA_X_FURO * math.sin(ang_guia))
    rasgo = (cx - 50.0 * math.cos(ang_guia), cy - 50.0 * math.sin(ang_guia))
    return guia, rasgo


def sensor_solo(c, pos, ang_face, z_ponta=10.0):
    """Sensor capacitivo v2.0 (98 x 23 x 1,6 mm) espetado na terra; a face com componentes aponta para ang_face."""
    poly = [(-3, 0), (3, 0), (11.5, 10), (11.5, 98), (-11.5, 98), (-11.5, 10)]
    V, F = prisma_np(poly, -0.8, 0.8)  # (a, b, c): a largura, b comprimento, c espessura
    # componentes na face +c (frente)
    partes = [(V, F)]
    chip = caixa_np(-2.5, 80, 0.8, 2.5, 86, 2.3)
    reg = caixa_np(-6.5, 72, 0.8, -3.5, 75, 1.9)
    conector = caixa_np(-4.2, 91, 0.8, 4.2, 98, 6.3)
    # referencial: a -> lateral, b -> z, c -> direção da face
    fx = np.array([math.cos(ang_face), math.sin(ang_face), 0.0])  # normal da face
    ax = np.array([-math.sin(ang_face), math.cos(ang_face), 0.0])
    R = np.c_[ax, [0, 0, 1.0], fx]
    base = np.array([pos[0], pos[1], z_ponta])
    uvf = lambda co: np.c_[((co - base) @ ax + 11.5) / 23, ((co - base)[:, 2]) / 98]
    c.add("sensor_placa", (transf(V, R, base), F), "pcb_sensor", uv=uvf)
    c.add("sensor_chip", (transf(*chip[:1], R, base), chip[1]), "preto")
    c.add("sensor_reg", (transf(*reg[:1], R, base), reg[1]), "preto")
    c.add("sensor_conector", (transf(*conector[:1], R, base), conector[1]), "branco", bevel=0.3)
    topo_conector = base + R @ np.array([0, 98, 3.55])
    return topo_conector


def cabo_paralelo(c, nome, pontos, mats, r=0.65, sep=1.35, passo=0.8, desloc=(0, 0, 0)):
    C = spline(np.asarray(pontos, float) + np.asarray(desloc, float), passo)
    T, N, B = quadros(C)
    k = len(mats)
    for i, mt in enumerate(mats):
        off = (i - (k - 1) / 2) * sep
        Ci = C + off * N
        c.add(f"{nome}_{i}", tubo_np(None, r, n=10, C=Ci, quadro=(T, N, B)), mt, suave=60)


def am2302(c, d=(0, 0, 0), dz=0.0):
    """AM2302 (caixa branca ~59 x 27 x 10) sobre a tampa, preso por 2 abraçadeiras."""
    z0 = EXT_Z + 2 + dz
    y0, y1 = Y_MEIO - 13.5, Y_MEIO + 13.5
    corpo = prisma_np(ret_arred(52, 27, 1.5, 4, cx=X_DHT + 7 + 26, cy=Y_MEIO), z0, z0 + 10)
    c.add("am2302_corpo", corpo, "branco", d, bevel=0.5)
    aba = prisma_np(ret_arred(9, 12, 1.5, 4, cx=X_DHT + 4.5, cy=Y_MEIO), z0, z0 + 2.2)
    c.add("am2302_aba", aba, "branco", d)
    c.add("am2302_furo", cilindro_np(1.6, z0 + 0.5, z0 + 2.25, 24, X_DHT + 3.6, Y_MEIO), "preto", d)
    # grade: aberturas escuras no topo
    grade = []
    for i in range(6):
        for j in range(4):
            xc = X_DHT + 17 + i * 7.2
            yc = Y_MEIO - 8.1 + j * 5.4
            grade.append(prisma_np(ret_arred(5.2, 2.6, 0.8, 3, cx=xc, cy=yc), z0 + 9.4, z0 + 10.03))
    c.add("am2302_grade", juntar(grade), "preto", d)
    # fios (vermelho, amarelo, preto) até o furo da tampa em x ~ 77,7
    xf = X_DHT + 59 + 6
    cabo_paralelo(c, "am2302_fios", [(X_DHT + 59 - 1, Y_MEIO, z0 + 4), (X_DHT + 61.5, Y_MEIO, z0 + 4.2),
                                     (xf - 0.5, Y_MEIO, z0 + 2.5), (xf, Y_MEIO, z0 - 1.5), (xf, Y_MEIO, z0 - 6)],
                  ["vermelho", "amarelo_fio", "preto_fio"], r=0.6, sep=1.25, passo=0.4, desloc=d)
    # abraçadeiras (fita 2,6 x 1,0) passando pelos rasgos da tampa
    for k, dx in enumerate((8 + 1.5, 59 - 14 + 1.5)):
        x = X_DHT + dx
        ya, yb = y0 - 2.6, y1 + 2.6
        pts = [(x, ya, z0 - 5), (x, ya, z0), (x, ya + 0.4, z0 + 8.6), (x, y0 + 0.9, z0 + 10.55),
               (x, Y_MEIO, z0 + 10.6), (x, y1 - 0.9, z0 + 10.55), (x, yb - 0.4, z0 + 8.6), (x, yb, z0),
               (x, yb, z0 - 5)]
        c.add(f"abracadeira_{k}", fita_np(pts, 2.6, 1.0, (1, 0, 0), passo=0.35), "preto", d)
        cab = caixa_np(x - 2.4, y1 - 9, z0 + 10.6, x + 2.4, y1 - 3.5, z0 + 14.0)
        c.add(f"abracadeira_cab_{k}", cab, "preto", d, bevel=0.4)


def bomba_e_agua(c, d=(0, 0, 0), agua=True, dz=0.0, mangueira_pts=None, fio_pts=None):
    """Bomba JT100 (~45 x 30 x 25, preta) no fundo do reservatório, perto de x ~ 150."""
    cx, cy = 147.0, -46.0
    z0 = 2.0 + dz
    corpo = prisma_np(ret_arred(45, 30, 7, 8, cx=cx, cy=cy), z0, z0 + 25)
    c.add("bomba", corpo, "preto", d, bevel=1.2)
    c.add("bomba_bico", cilindro_np(3.2, z0 + 25, z0 + 29, 32, 160, cy), "preto", d, suave=40)
    c.add("bomba_bico2", cilindro_np(1.7, z0 + 29, z0 + 36, 24, 160, cy), "preto", d, suave=40)
    c.add("bomba_bota", cilindro_np(2.6, z0 + 25, z0 + 28, 24, 132, cy), "preto", d, suave=40)
    c.add("bomba_entrada", cilindro_eixo((cx - 22.6, cy, z0 + 12.5), (cx - 23.6, cy, z0 + 12.5), 6.0),
          "preto_fosco", d)
    if agua:
        c.add("agua", caixa_np(2.46, -RES_EXT_Y + 2.46, 2.05, EXT_X - 2.46, -6.06, 31.0), "agua", d)
    if mangueira_pts is not None:
        c.add("mangueira", tubo_np(mangueira_pts, 2.5, n=20, r_int=1.6, passo=0.8), "mangueira", suave=60)
    if fio_pts is not None:
        cabo_paralelo(c, "fio_bomba", fio_pts, ["vermelho", "preto_fio"], r=0.7, sep=1.45)


def eletronica(c, d=(0, 0, 0), fios=True):
    """Protoboard 165x80 no fundo da caixa, ESP32-S3 na ponta x=0 (USB virada para o rasgo),
    MPSA42 + 1 kΩ + 1N4007 na ponta x ~ 170."""
    zp = 2.0
    zt = zp + 9.5  # topo da protoboard
    c.add("protoboard", caixa_np(4.4, 4.4, zp, 169.4, 84.4, zt), "branco_proto", d,
          uv=lambda co: np.c_[(co[:, 0] - 4.4) / 165, (co[:, 1] - 4.4) / 80], bevel=0.5)
    # ESP32-S3 DevKit (69 x 26), porta usada centrada em y = 44,4
    yc = Y_MEIO + 4.5
    x0, x1 = 6.0, 75.0
    zpcb = zt + 2.5
    c.add("esp32_pcb", caixa_np(x0, yc - 13, zpcb, x1, yc + 13, zpcb + 1.6), "pcb_esp", d,
          uv=lambda co: np.c_[(co[:, 0] - x0) / 69, (co[:, 1] - (yc - 13)) / 26])
    for yy in (yc - 11.4, yc + 11.4):
        c.add("esp32_barra", caixa_np(8.5, yy - 1.25, zt, 63.5, yy + 1.25, zpcb), "preto", d)
    zs = zpcb + 1.6
    c.add("esp32_modulo", caixa_np(47, yc - 9, zs, 72.5, yc + 9, zs + 0.8), "pcb_preto", d)
    c.add("esp32_blindagem", caixa_np(47.6, yc - 8.4, zs + 0.8, 64.5, yc + 8.4, zs + 3.2), "metal", d, bevel=0.3)
    for k, yy in enumerate((Y_MEIO, Y_MEIO + 9.0)):
        usb = prisma_np(ret_arred(8.9, 3.2, 1.3, 6), 0, 7.4)
        V = transf(usb[0], np.array([[0, 0, 1.0], [1.0, 0, 0], [0, 1.0, 0]]), (5.2, yy, zs + 1.6))
        c.add(f"esp32_usb{k}", (V, usb[1]), "metal", d, suave=40)
    for yy in (yc - 9.5, yc + 9.5):
        c.add("esp32_botao_base", caixa_np(14, yy - 2, zs, 18.5, yy + 2, zs + 1.2), "metal", d)
        c.add("esp32_botao", cilindro_np(1.0, zs + 1.2, zs + 1.9, 16, 16.25, yy), "preto", d)
    c.add("esp32_led", caixa_np(24, yc + 7, zs, 25.6, yc + 8.6, zs + 0.7), "branco", d)
    # transistor MPSA42 (TO-92): face reta para -x
    xt, ytr = 160.0, 31.0
    a = np.linspace(-math.pi / 2, math.pi / 2, 16)
    poly = [(xt - 1.2, ytr - 2.3)] + [(xt + 2.3 * math.cos(t), ytr + 2.3 * math.sin(t)) for t in a] +            [(xt - 1.2, ytr + 2.3)]
    c.add("mpsa42", prisma_np(poly, zt + 3, zt + 7.5), "preto", d, suave=40)
    for dy in (-1.27, 0, 1.27):
        c.add("mpsa42_perna", cilindro_np(0.25, zt, zt + 3, 8, xt + 0.8, ytr + dy), "prata", d)
    # resistor 1 kΩ (marrom, preto, vermelho, dourado)
    yr = 22.0
    c.add("resistor", cilindro_eixo((147, yr, zt + 2.6), (153.3, yr, zt + 2.6), 1.15, 24), "bege", d, suave=40)
    for k, (xx, mt) in enumerate(((148.0, "marrom"), (149.2, "preto_fio"), (150.4, "vermelho"), (152.3, "dourado"))):
        c.add(f"faixa{k}", cilindro_eixo((xx, yr, zt + 2.6), (xx + 0.6, yr, zt + 2.6), 1.2, 24), mt, d, suave=40)
    for xx in (144.9, 155.4):
        c.add("resistor_perna", tubo_np([(xx, yr, zt), (xx, yr, zt + 2.0), (xx + (1.5 if xx < 150 else -1.5), yr, zt + 2.6)],
                                        0.25, n=8, passo=0.3), "prata", d)
    # diodo 1N4007 (preto com faixa prata)
    yd = 58.0
    c.add("diodo", cilindro_eixo((147.4, yd, zt + 2.9), (152.6, yd, zt + 2.9), 1.35, 24), "preto", d, suave=40)
    c.add("diodo_faixa", cilindro_eixo((151.4, yd, zt + 2.9), (152.2, yd, zt + 2.9), 1.4, 24), "prata", d, suave=40)
    for xx in (144.9, 155.1):
        c.add("diodo_perna", tubo_np([(xx, yd, zt), (xx, yd, zt + 2.3), (xx + (2.0 if xx < 150 else -2.0), yd, zt + 2.9)],
                                     0.3, n=8, passo=0.3), "prata", d)
    if not fios:
        return
    # jumpers na protoboard
    jumpers = [
        ("vermelho", (70, yc + 12.7), (120, 80.5), 9),
        ("preto_fio", (66, yc - 12.7), (120, 8.2), 8),
        ("verde", (52, yc + 12.7), (163, 44.4), 14),
        ("amarelo_fio", (57, yc + 12.7), (82, 70), 8),
        ("laranja", (61, yc - 12.7), (144.9, yr), 12),
        ("azul", (130, 8.2), (160.8, ytr - 1.27), 7),
        ("preto_fio", (155.1, yd), (163.0, 17.8), 6),
    ]
    for k, (mt, p0, p1, h) in enumerate(jumpers):
        q0 = np.array([p0[0], p0[1], zt])
        q1 = np.array([p1[0], p1[1], zt])
        meio = (q0 + q1) / 2
        pts = [q0, q0 + [0, 0, h * 0.6], meio + [0, 0, h], q1 + [0, 0, h * 0.6], q1]
        c.add(f"jumper{k}", tubo_np(pts, 0.55, n=10, passo=0.6), mt, d, suave=60)
    # conectores dupont dos cabos externos, junto dos rasgos
    for k, yy in enumerate((Y_CABOS[0], Y_CABOS[1])):
        c.add(f"dupont{k}", caixa_np(158, yy - 4, zt, 166, yy + 4, zt + 2.6), "preto", d)


def usb_c_estacao(c, d=(0, 0, 0)):
    """Plugue USB-C entrando pelo rasgo da face x=0 até a ESP32. Devolve a ponta do cabo."""
    zc = 2.0 + 9.5 + 2.5 + 1.6 + 1.6
    corpo = prisma_np(ret_arred(11, 6.5, 2.5, 6), 0, 22)
    V = transf(corpo[0], np.array([[0, 0, 1.0], [1.0, 0, 0], [0, 1.0, 0]]), (-17.0, Y_MEIO, zc))
    c.add("usbc_plugue", (V, corpo[1]), "preto_fosco", d, suave=40)
    c.add("usbc_alivio", cilindro_eixo((-27, Y_MEIO, zc), (-16.9, Y_MEIO, zc), 2.6, 24), "preto_fosco", d, suave=40)
    return np.array([-26.5, Y_MEIO, zc]) + np.asarray(d)


def notebook(c, centro, yaw_graus, aberto=True, porta="direita"):
    """Notebook 14" (320 x 220 x 15 mm), cinza grafite. Devolve a ponta do plugue USB-A e a direção do cabo."""
    L, P, A = 320.0, 220.0, 15.0
    Rz = rot_z(math.radians(yaw_graus))
    t = np.array([centro[0], centro[1], 0.0])
    W = lambda V: transf(V, Rz, t)
    base = prisma_np(ret_arred(L, P, 9, 8), 0.0, A)
    c.add("nb_base", (W(base[0]), base[1]), "alu", bevel=1.2)
    tampo = prisma_np(ret_arred(L - 3, P - 3, 8, 8), A, A + 0.12)
    uv = lambda co: np.c_[((co - t) @ Rz[:, 0] + 160) / 320, ((co - t) @ Rz[:, 1] + 110) / 220]
    c.add("nb_tampo", (W(tampo[0]), tampo[1]), "tampo", uv=uv)
    # tampa (tela)
    hinge = np.array([0.0, P / 2 - 5.0, A])
    if aberto:
        alfa = math.radians(18)  # inclinação para trás a partir da vertical
        U = np.array([0, math.sin(alfa), math.cos(alfa)])
        Nf = np.array([0, -math.cos(alfa), math.sin(alfa)])
    else:
        U = np.array([0, -1.0, 0])
        Nf = np.array([0, 0, -1.0])
        hinge = np.array([0.0, P / 2 - 3.0, A + 0.15])
    X = np.array([1.0, 0, 0])

    def placa(w, h, w0, w1, nome, mat, r=8, desloc_t=0.0, uv=None):
        poly = ret_arred(w, h, r, 8, cy=h / 2 + desloc_t)
        V, F = prisma_np(poly, w0, w1)  # x, t, profundidade
        V3 = hinge + V[:, :1] * X + V[:, 1:2] * U - V[:, 2:3] * Nf
        return c.add(nome, (W(V3), F), mat, uv=uv, bevel=(0.8 if mat == "alu" else None))

    placa(L, 214, 0.6, 5.8, "nb_tampa", "alu")
    placa(L - 1.2, 212.8, 0.0, 0.6, "nb_moldura", "vidro_preto", desloc_t=0.6)
    if aberto:
        # painel da tela 300 x 187,5 (16:10)
        w, h, t0 = 300.0, 187.5, 13.0
        poly = [(-w / 2, t0), (w / 2, t0), (w / 2, t0 + h), (-w / 2, t0 + h)]
        V, F = prisma_np(poly, -0.05, 0.0)
        V3 = hinge + V[:, :1] * X + V[:, 1:2] * U - V[:, 2:3] * Nf
        Vw = W(V3)
        org = W(hinge[None, :] + t0 * U[None, :])[0]
        eu, ev = Rz @ X, Rz @ U
        c.add("nb_tela", (Vw, F), "tela", uv=lambda co: np.c_[((co - org) @ eu + w / 2) / w, ((co - org) @ ev) / h])
    c.add("nb_dobradica", cilindro_eixo(W(np.array([[-120, P / 2 - 5, A - 1]]))[0],
                                        W(np.array([[120, P / 2 - 5, A - 1]]))[0], 4.5, 24), "alu_escuro", suave=40)
    # porta USB e plugue USB-A
    sx = 1 if porta == "direita" else -1
    xp = sx * L / 2
    yp = -25.0
    c.add("nb_porta", (W(caixa_np(xp - 0.6 * sx - 0.01, yp - 6.5, 4.2, xp + 0.05 * sx, yp + 6.5, 10.2)[0]),
                       caixa_np(0, 0, 0, 1, 1, 1)[1]), "preto")
    metal = caixa_np(min(xp, xp + 4 * sx), yp - 6, 5.0, max(xp, xp + 4 * sx), yp + 6, 9.5)
    c.add("usba_metal", (W(metal[0]), metal[1]), "metal")
    corpo = prisma_np(ret_arred(22, 16, 3, 6), -4.2, 4.2)
    Vc = transf(corpo[0], None, (xp + sx * 15, yp, 7.25))
    c.add("usba_plugue", (W(Vc), corpo[1]), "preto_fosco", bevel=1.0)
    ponta = W(np.array([[xp + sx * 27.5, yp, 7.25]]))[0]
    direcao = Rz @ np.array([sx, 0, 0.0])
    alivio = cilindro_eixo(W(np.array([[xp + sx * 25.5, yp, 7.25]]))[0], ponta + direcao * 3, 2.7, 24)
    c.add("usba_alivio", alivio, "preto_fosco", suave=40)
    return ponta + direcao * 2.5, direcao




def plano_grade(x0, y0, x1, y1, z=0.0, passo=50.0):
    nx, ny = int(np.ceil((x1 - x0) / passo)), int(np.ceil((y1 - y0) / passo))
    xs, ys = np.linspace(x0, x1, nx + 1), np.linspace(y0, y1, ny + 1)
    X, Y = np.meshgrid(xs, ys)
    V = np.c_[X.ravel(), Y.ravel(), np.full(X.size, z)]
    F = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            F.append([a, a + 1, a + nx + 2, a + nx + 1])
    return V, F


def mesa(c, x=(-3000, 3000), y=(-800, 700), parede=True):
    c.add("mesa", plano_grade(x[0], y[0], x[1], y[1], 0.0, 50.0), "madeira")
    if parede:
        # parede clara atrás da mesa (vertical, em y = y[1])
        V, F = plano_grade(x[0], 0.0, x[1], 1600.0, 0.0, 100.0)
        V = np.c_[V[:, 0], np.full(len(V), y[1]), V[:, 1]]
        c.add("parede", (V, F), "parede")


def caminho_usb(p0, d0, p1, raio=2.2, folga=(0.0, 0.0)):
    """Cabo USB do notebook até a estação: sai do plugue, deita na mesa e sobe até o plugue USB-C."""
    p0, p1, d0 = np.asarray(p0, float), np.asarray(p1, float), np.asarray(d0, float)
    a = p0 + d0 * 18 + [0, 0, -3.0]
    b = p0 + d0 * 42
    b[2] = raio
    e = p1 + np.array([-40.0, 0, 0])
    e[2] = raio
    m = (b + e) / 2 + np.array([folga[0], folga[1], 0])
    m[2] = raio
    f = p1 + np.array([-16.0, 0, -6.0])
    return [p0, a, b, m, e, f, p1]



def estacao_completa(c, tampa=True, fios_internos=False, internos=False, notebook_cfg=None, d=(0, 0, 0),
                     vaso_c=VASO_C):
    d = np.asarray(d, float)
    pecas_impressas(c, d, tampa=tampa)
    if tampa:
        am2302(c, d)
    if internos:
        eletronica(c, d, fios=fios_internos)
    guia, rasgo = coroa_e_vaso(c, vaso_c, ANG_GUIA)
    gx, gy = guia
    # mangueira: bico da bomba -> sobe, arco por cima e desce na guia da coroa (vem pela frente)
    bico = d + [160, -46, 33]
    mang = [bico, bico + [0, 0, 14], bico + [3, -4, 30], d + [183, -62, 80],
            ((d[0] + 183 + gx) / 2 + 8, gy - 30, 97), (gx, gy - 17, 98), (gx, gy - 6, 90), (gx, gy, 83), (gx, gy, 71)]
    fio = [d + [132, -46, 30], d + [134, -42, 44], d + [142, -26, 53], d + [160, -9, 53], d + [178.5, 3, 47],
           d + [180, 14, 39], d + [176, Y_CABOS[0], 35], d + [169, Y_CABOS[0], 33], d + [165, Y_CABOS[0], 28]]
    bomba_e_agua(c, d, mangueira_pts=mang, fio_pts=fio)
    # sensor de solo perto do rasgo (lado +y do vaso), face com componentes para a frente
    vx, vy = vaso_c
    topo = sensor_solo(c, (vx, vy + 20), -math.pi / 2)
    rx, ry = rasgo
    alvo_rasgo = d + [EXT_X, Y_CABOS[1], 34]
    pts = [topo, topo + [0, 0, 5], (vx, vy + 25, topo[2] + 6), (vx, ry - 9, 88), (rx, ry - 2.5, 80.9),
           (rx, ry + 2.5, 80.0), (rx - 1, ry + 7.5, 73), (vx - 10, ry + 16, 60),
           (alvo_rasgo[0] + 30, alvo_rasgo[1] + 10, alvo_rasgo[2] + 6), alvo_rasgo + [8, 0, 1],
           alvo_rasgo + [-3, 0, -0.5], alvo_rasgo + [-12, 0, -6]]
    cabo_paralelo(c, "cabo_sensor", pts, ["preto_fio", "vermelho", "amarelo_fio"], r=0.65, sep=1.35)
    ponta_c = usb_c_estacao(c, d)
    if notebook_cfg:
        p0, d0 = notebook(c, **notebook_cfg)
        cam = caminho_usb(p0, d0, ponta_c)
        c.add("cabo_usb", tubo_np(cam, 2.2, n=16, passo=1.0), "preto_fosco", suave=60)


def guia_tracejada(c, x, y, z0, z1, r=0.45, traco=4.0, vao=3.0):
    partes = []
    z = z0
    while z < z1:
        partes.append(cilindro_np(r, z, min(z + traco, z1), 10, x, y))
        z += traco + vao
    if partes:
        c.add("guia", juntar(partes), "guia")


# ----------------------------------------------------------------------
# Montagens de cada imagem (só geometria; câmera e luz ficam no render_sit.py)
# ----------------------------------------------------------------------

def montar_hero():
    c = Cena()
    mesa(c)
    estacao_completa(c, notebook_cfg=NOTEBOOK_MESA)
    return c


def montar_interno():
    c = Cena()
    mesa(c)
    estacao_completa(c, tampa=False, internos=True, fios_internos=True, notebook_cfg=NOTEBOOK_MESA)
    return c


EXPLODIDA = dict(dz_caixa=62.0, dz_tampa=85.0, dz_coroa=55.0, vaso=(275.0, 40.0))


def montar_explodida():
    """Vista explodida vertical: o reservatório fica no piso; a caixa sobe pelos rabos de andorinha
    (eles deslizam na vertical), a tampa sobe acima da caixa e a coroa sobe acima do vaso."""
    c = Cena()
    c.add("piso", plano_grade(-1600, -1400, 1800, 1800, 0.0, 100.0), "piso")
    e = EXPLODIDA
    zc, dz_t, dz_c, vaso = e["dz_caixa"], e["dz_tampa"], e["dz_coroa"], e["vaso"]
    d = np.array([0.0, 0.0, zc])
    pecas_impressas(c, d, tampa=True, dz_tampa=dz_t, dz_res=-zc)
    am2302(c, d, dz=dz_t)
    eletronica(c, d, fios=False)
    bomba_e_agua(c, np.zeros(3), agua=False)
    coroa_e_vaso(c, vaso, ANG_GUIA, dz_coroa=dz_c)
    # guias tracejadas de montagem (verticais)
    for (x, y) in ((0.6, EXT_Y - 0.6), (EXT_X - 0.6, EXT_Y - 0.6)):
        guia_tracejada(c, x, y, 1, zc - 1)
    for (x, y) in ((0.6, 0.6), (EXT_X - 0.6, 0.6), (EXT_X - 0.6, EXT_Y - 0.6)):
        guia_tracejada(c, x, y, zc + EXT_Z + 1, zc + EXT_Z + dz_t - 3)
    for ang in (math.pi * 0.75, math.pi * 1.25):
        guia_tracejada(c, vaso[0] + 52 * math.cos(ang), vaso[1] + 52 * math.sin(ang), 81, 67 + dz_c - 1)
    c.rotulos = {
        "Tampa com sensor AM2302": (20, 15, zc + EXT_Z + 2 + dz_t),
        "Caixa da eletrônica (ESP32-S3)": (15, 0, zc + 30),
        "Reservatório com bomba": (15, -RES_EXT_Y, 21),
        "Coroa do vaso": (vaso[0] + 53, vaso[1], 82 + dz_c - 7),
        "Vaso com terra": (vaso[0] + 40, vaso[1] - 20, 28),
    }
    return c


def montar_sobre_notebook():
    c = Cena()
    mesa(c)
    nb_c, A = (40.0, 60.0), 15.0 + 0.15 + 5.8
    d = np.array([nb_c[0] - 100.0, nb_c[1] - 2.0, A])
    vaso = (nb_c[0] + 160 + 80, nb_c[1] - 40)
    pecas_impressas(c, d)
    am2302(c, d)
    guia, rasgo = coroa_e_vaso(c, vaso, ANG_GUIA)
    gx, gy = guia
    bico = d + [160, -46, 33]
    mang = [bico, bico + [0, 0, 14], bico + [4, -6, 34], d + [190, -66, 70], (gx - 25, gy - 32, 102),
            (gx, gy - 16, 98), (gx, gy - 6, 90), (gx, gy, 83), (gx, gy, 71)]
    fio = [d + [132, -46, 30], d + [134, -42, 44], d + [142, -26, 53], d + [160, -9, 53], d + [178.5, 3, 47],
           d + [180, 14, 39], d + [176, Y_CABOS[0], 35], d + [169, Y_CABOS[0], 33], d + [165, Y_CABOS[0], 28]]
    bomba_e_agua(c, d, mangueira_pts=mang, fio_pts=fio)
    vx, vy = vaso
    topo = sensor_solo(c, (vx, vy + 20), -math.pi / 2)
    rx, ry = rasgo
    alvo = d + [EXT_X, Y_CABOS[1], 34]
    pts = [topo, topo + [0, 0, 5], (vx, vy + 25, topo[2] + 6), (vx, ry - 9, 88), (rx, ry - 2.5, 80.9),
           (rx, ry + 2.5, 80.0), (rx - 2, ry + 9, 76), (rx - 30, ry + 20, 80), (alvo[0] + 25, alvo[1] + 8, alvo[2] + 8),
           alvo + [8, 0, 1], alvo + [-3, 0, -0.5], alvo + [-12, 0, -6]]
    cabo_paralelo(c, "cabo_sensor", pts, ["preto_fio", "vermelho", "amarelo_fio"], r=0.65, sep=1.35)
    ponta_c = usb_c_estacao(c, d)
    p0, d0 = notebook(c, nb_c, 0, aberto=False, porta="esquerda")
    pts = [p0, p0 + d0 * 14 + [0, 0, -1], p0 + d0 * 30 + [0, -6, 8],
           (ponta_c[0] - 30, ponta_c[1] - 40, ponta_c[2] + 18), ponta_c + [-16, 0, 2], ponta_c]
    c.add("cabo_usb", tubo_np(pts, 2.2, n=16, passo=1.0), "preto_fosco", suave=60)
    return c


MONTAGENS = {"hero": montar_hero, "closeup": montar_hero, "interno": montar_interno,
             "explodida": montar_explodida, "sobre_notebook": montar_sobre_notebook}
