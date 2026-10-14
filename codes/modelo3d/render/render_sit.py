"""
Renderizador próprio (numpy + OpenCV) das imagens da estação SIT, pensado para pouca memória.

- Rasterização com z-buffer, por tiles, e sombreamento diferido.
- Sombra suave da luz principal (PCSS) e oclusão de céu por mapas de sombra em várias direções.
- Reflexo de ambiente de estúdio com Fresnel; metais, plásticos e PETG levemente brilhante.
- Água e mangueira translúcidas (camadas compostas por cima do opaco).
- Superamostragem 2x (padrão) e tone mapping Khronos PBR Neutral; saída PNG 1920x1080.

Uso:
  python codes/modelo3d/render/render_sit.py --cena hero        (hero, closeup, interno, explodida, sobre_notebook)
  python codes/modelo3d/render/render_sit.py --cena hero --previa   (rápido, sem superamostragem)
"""

import argparse
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geometria_sit as G  # noqa: E402

AQUI = Path(__file__).resolve().parent
TEX = AQUI / "tex"
SAIDA = G.RAIZ / "outputs" / "renders"
W_FINAL, H_FINAL = 1920, 1080


def lin(h):
    h = h.lstrip("#")
    c = np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def srgb_para_lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4).astype(np.float32)


# ----------------------------------------------------------------------
# Materiais: cor, brilho especular (ks, expoente), reflexo (f0, env), metal, textura/procedural, emissão
# ----------------------------------------------------------------------
MATS = {
    "petg": dict(cor="#F5C400", ks=0.35, sh=70, f0=0.05, env=0.9),
    "preto": dict(cor="#1D1D1E", ks=0.30, sh=60, f0=0.045, env=0.8),
    "preto_fosco": dict(cor="#171718", ks=0.12, sh=18, f0=0.04, env=0.35),
    "branco": dict(cor="#ECEBE6", ks=0.22, sh=40, f0=0.04, env=0.5),
    "branco_proto": dict(cor="#F3F2EC", ks=0.15, sh=30, f0=0.04, env=0.35, tex="protoboard.png"),
    "metal": dict(cor="#C9CBCE", ks=0.9, sh=110, f0=0.75, env=1.0, metal=True),
    "dourado": dict(cor="#D8B25A", ks=0.8, sh=80, f0=0.6, env=1.0, metal=True),
    "pcb_sensor": dict(cor="#151515", ks=0.35, sh=70, f0=0.05, env=0.9, tex="sensor_pcb.png"),
    "pcb_esp": dict(cor="#141414", ks=0.35, sh=70, f0=0.05, env=0.9, tex="esp32_pcb.png"),
    "pcb_preto": dict(cor="#141414", ks=0.35, sh=70, f0=0.05, env=0.9),
    "terracota": dict(cor="#B85B34", ks=0.06, sh=12, f0=0.03, env=0.15, proc="terracota"),
    "terra": dict(cor="#3A2A1E", ks=0.02, sh=8, f0=0.02, env=0.04, proc="terra"),
    "madeira": dict(cor="#E0C59A", ks=0.10, sh=25, f0=0.04, env=0.30, proc="madeira"),
    "alu": dict(cor="#8E939A", ks=0.35, sh=45, f0=0.06, env=0.55),
    "alu_escuro": dict(cor="#3A3C40", ks=0.3, sh=40, f0=0.05, env=0.5),
    "vidro_preto": dict(cor="#0B0B0C", ks=0.9, sh=220, f0=0.05, env=1.0),
    "tampo": dict(cor="#565A61", ks=0.25, sh=40, f0=0.2, env=0.5, tex="teclado.png"),
    "tela": dict(cor="#000000", ks=0.6, sh=220, f0=0.04, env=0.5, tex="dashboard.png", emis=0.92),
    "vermelho": dict(cor="#C8322A", ks=0.3, sh=50, f0=0.045, env=0.6),
    "amarelo_fio": dict(cor="#E8B90F", ks=0.3, sh=50, f0=0.045, env=0.6),
    "verde": dict(cor="#2E9A44", ks=0.3, sh=50, f0=0.045, env=0.6),
    "laranja": dict(cor="#E2741E", ks=0.3, sh=50, f0=0.045, env=0.6),
    "azul": dict(cor="#2F5FC4", ks=0.3, sh=50, f0=0.045, env=0.6),
    "preto_fio": dict(cor="#202020", ks=0.3, sh=50, f0=0.045, env=0.6),
    "marrom": dict(cor="#6B3B1F", ks=0.2, sh=40, f0=0.04, env=0.4),
    "bege": dict(cor="#D8C49A", ks=0.2, sh=40, f0=0.04, env=0.4),
    "prata": dict(cor="#D9D9D9", ks=0.8, sh=90, f0=0.7, env=1.0, metal=True),
    "creme": dict(cor="#FBF6E6", ks=0.05, sh=10, f0=0.03, env=0.1),
    "guia": dict(cor="#8A8170", ks=0.05, sh=10, f0=0.03, env=0.1),
    "piso": dict(cor="#FBF6E6", ks=0.0, sh=10, f0=0.0, env=0.0, proc="piso"),
    "parede": dict(cor="#EEE7D8", ks=0.0, sh=10, f0=0.0, env=0.0),
    "agua": dict(cor="#3D8FC9", transp=True),
    "mangueira": dict(cor="#E8F1F4", transp=True),
}
NOMES = list(MATS)
ID = {n: i for i, n in enumerate(NOMES)}
NAO_PROJETAM = {"mesa", "piso", "parede"}  # superfícies que só recebem sombra


def tabela(campo, padrao=0.0):
    return np.array([MATS[n].get(campo, padrao) for n in NOMES], np.float32)


PAL = np.stack([lin(MATS[n]["cor"]) for n in NOMES])
KS, SH, F0, ENV, EMIS = tabela("ks"), tabela("sh", 10), tabela("f0"), tabela("env"), tabela("emis")
METAL = tabela("metal").astype(bool)


# ----------------------------------------------------------------------
# Malhas -> triângulos com normais suavizadas por ângulo e UV
# ----------------------------------------------------------------------

def triangular(F):
    T = []
    for f in F:
        for i in range(1, len(f) - 1):
            T.append((f[0], f[i], f[i + 1]))
    return np.array(T, np.int64)


def normais_cantos(V, T, suave):
    p0, p1, p2 = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    fn = np.cross(p1 - p0, p2 - p0)
    nrm = np.linalg.norm(fn, axis=1)
    fu = fn / np.maximum(nrm, 1e-12)[:, None]
    if suave is None:
        return np.repeat(fu[:, None, :], 3, axis=1)
    cos_lim = math.cos(math.radians(suave))
    cv = T.ravel()
    cf = np.repeat(np.arange(len(T)), 3)
    ordem = np.argsort(cv, kind="stable")
    cv_s, cf_s = cv[ordem], cf[ordem]
    cont = np.bincount(cv, minlength=len(V))
    ini = np.r_[0, np.cumsum(cont)[:-1]]
    k = cont[cv_s]
    s = ini[cv_s]
    rep = np.repeat(np.arange(len(cv_s)), k)
    offs = np.arange(len(rep)) - np.repeat(np.cumsum(k) - k, k)
    j = s[rep] + offs
    fi, fj = cf_s[rep], cf_s[j]
    w = ((fu[fi] * fu[fj]).sum(1) > cos_lim).astype(float)
    acc = np.stack([np.bincount(rep, weights=fn[fj, d] * w, minlength=len(cv_s)) for d in range(3)], 1)
    acc /= np.maximum(np.linalg.norm(acc, axis=1), 1e-12)[:, None]
    out = np.empty_like(acc)
    out[ordem] = acc
    return out.reshape(-1, 3, 3)


class Triangulos:
    def __init__(self, cena):
        P, N, UV, M, PROJ, NOMES_M = [], [], [], [], [], []
        for m in cena.malhas:
            V = np.asarray(m["V"], float)
            T = triangular(m["F"])
            if len(T) == 0:
                continue
            P.append(V[T].astype(np.float32))
            N.append(normais_cantos(V, T, m["suave"]).astype(np.float32))
            if m["uv"] is not None:
                uv = np.asarray(m["uv"](V), float)
                UV.append(uv[T].astype(np.float32))
            else:
                UV.append(np.zeros((len(T), 3, 2), np.float32))
            M.append(np.full(len(T), ID[m["mat"]], np.int16))
            PROJ.append(np.full(len(T), m["nome"] not in NAO_PROJETAM and not MATS[m["mat"]].get("transp"), bool))
            NOMES_M.append(np.full(len(T), len(NOMES_M), np.int32))
        self.P = np.concatenate(P)
        self.N = np.concatenate(N)
        self.UV = np.concatenate(UV)
        self.M = np.concatenate(M)
        self.proj = np.concatenate(PROJ)

    def subconjunto(self, mask):
        s = Triangulos.__new__(Triangulos)
        s.P, s.N, s.UV, s.M, s.proj = self.P[mask], self.N[mask], self.UV[mask], self.M[mask], self.proj[mask]
        return s


# ----------------------------------------------------------------------
# Rasterizador (z-buffer, coordenadas baricêntricas corrigidas pela perspectiva)
# ----------------------------------------------------------------------

def rasterizar(X, Y, Z, W, H, persp=True, so_prof=False, perto=1.0, max_frag=1_000_000):
    zbuf = np.full(W * H, np.inf, np.float32)
    tbuf = b1b = b2b = None
    if not so_prof:
        tbuf = np.full(W * H, -1, np.int32)
        b1b = np.zeros(W * H, np.float32)
        b2b = np.zeros(W * H, np.float32)
    X = X.astype(np.float64)
    Y = Y.astype(np.float64)
    x0, x1, x2 = X[:, 0], X[:, 1], X[:, 2]
    y0, y1, y2 = Y[:, 0], Y[:, 1], Y[:, 2]
    area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    ok = np.isfinite(area) & (np.abs(area) > 1e-10)
    if persp:
        ok &= (Z > perto).all(1)
    i0 = np.ceil(X.min(1) - 0.5)
    i1 = np.floor(X.max(1) - 0.5)
    j0 = np.ceil(Y.min(1) - 0.5)
    j1 = np.floor(Y.max(1) - 0.5)
    ok &= (i1 >= 0) & (i0 <= W - 1) & (j1 >= 0) & (j0 <= H - 1) & (i0 <= i1) & (j0 <= j1)
    idx = np.nonzero(ok)[0]
    if len(idx) == 0:
        return zbuf, tbuf, b1b, b2b
    i0 = np.clip(i0[idx], 0, W - 1).astype(np.int64)
    i1 = np.clip(i1[idx], 0, W - 1).astype(np.int64)
    j0 = np.clip(j0[idx], 0, H - 1).astype(np.int64)
    j1 = np.clip(j1[idx], 0, H - 1).astype(np.int64)
    ar = area[idx]
    xa, xb, xc = x0[idx], x1[idx], x2[idx]
    ya, yb, yc = y0[idx], y1[idx], y2[idx]
    A0, B0, C0 = (xb * yc - xc * yb) / ar, (yb - yc) / ar, (xc - xb) / ar
    A1, B1, C1 = (xc * ya - xa * yc) / ar, (yc - ya) / ar, (xa - xc) / ar
    Zs = Z[idx].astype(np.float64)
    lado = np.maximum(i1 - i0 + 1, j1 - j0 + 1)
    classe = np.ceil(np.log2(np.maximum(lado, 1))).astype(np.int64)
    for kc in np.unique(classe):
        sel = np.nonzero(classe == kc)[0]
        s = 1 << int(kc)
        lote = max(1, max_frag // (s * s))
        g = np.arange(s)
        for a in range(0, len(sel), lote):
            ids = sel[a:a + lote]
            PX = i0[ids][:, None] + g[None, :]
            PY = j0[ids][:, None] + g[None, :]
            m = (PY <= j1[ids][:, None])[:, :, None] & (PX <= i1[ids][:, None])[:, None, :]
            bi, yy, xx = np.nonzero(m)
            if len(bi) == 0:
                continue
            px, py = PX[bi, xx], PY[bi, yy]
            t = ids[bi]
            cx, cy = px + 0.5, py + 0.5
            w0 = A0[t] + B0[t] * cx + C0[t] * cy
            w1 = A1[t] + B1[t] * cx + C1[t] * cy
            w2 = 1.0 - w0 - w1
            dentro = (w0 >= -1e-7) & (w1 >= -1e-7) & (w2 >= -1e-7)
            if not dentro.any():
                continue
            px, py, t, w0, w1, w2 = px[dentro], py[dentro], t[dentro], w0[dentro], w1[dentro], w2[dentro]
            z0, z1, z2 = Zs[t, 0], Zs[t, 1], Zs[t, 2]
            if persp:
                iz = w0 / z0 + w1 / z1 + w2 / z2
                z = 1.0 / iz
                b1 = w1 / z1 / iz
                b2 = w2 / z2 / iz
            else:
                z = w0 * z0 + w1 * z1 + w2 * z2
                b1, b2 = w1, w2
            p = py * W + px
            z32 = z.astype(np.float32)
            np.minimum.at(zbuf, p, z32)
            if not so_prof:
                ganha = z32 <= zbuf[p]
                pg = p[ganha]
                tbuf[pg] = idx[t[ganha]]
                b1b[pg] = b1[ganha]
                b2b[pg] = b2[ganha]
    return zbuf, tbuf, b1b, b2b


# ----------------------------------------------------------------------
# Câmera e mapas de sombra
# ----------------------------------------------------------------------

class Camera:
    def __init__(self, pos, alvo, lente, W, H):
        self.pos = np.asarray(pos, float)
        f = np.asarray(alvo, float) - self.pos
        f /= np.linalg.norm(f)
        r = np.cross(f, [0, 0, 1.0])
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        self.R = np.stack([r, u, f])
        self.f = W * lente / 36.0
        self.W, self.H = W, H

    def projetar(self, P, ox=0.0, oy=0.0):
        q = (P.reshape(-1, 3).astype(np.float64) - self.pos) @ self.R.T
        z = q[:, 2]
        x = self.W / 2 + self.f * q[:, 0] / z - ox
        y = self.H / 2 - self.f * q[:, 1] / z - oy
        forma = P.shape[:-1]
        return x.reshape(forma), y.reshape(forma), z.reshape(forma)


class MapaSombra:
    def __init__(self, L, tri, n, meia=False):
        self.L = np.asarray(L, float) / np.linalg.norm(L)
        ref = np.array([0, 0, 1.0]) if abs(self.L[2]) < 0.95 else np.array([1.0, 0, 0])
        self.u = np.cross(self.L, ref)
        self.u /= np.linalg.norm(self.u)
        self.v = np.cross(self.L, self.u)
        P = tri.P.reshape(-1, 3).astype(np.float64)
        pu, pv = P @ self.u, P @ self.v
        marg = 4.0
        self.umin, self.vmin = pu.min() - marg, pv.min() - marg
        ext = max(pu.max() + marg - self.umin, pv.max() + marg - self.vmin)
        self.esc = n / ext
        self.texel = ext / n
        self.n = n
        X, Y, Z = self.coords(tri.P)
        z, _, _, _ = rasterizar(X, Y, Z, n, n, persp=False, so_prof=True, max_frag=1_500_000)
        self.mapa = z.reshape(n, n).astype(np.float16 if meia else np.float32)

    def coords(self, P):
        P = np.asarray(P, np.float64)
        X = (P @ self.u - self.umin) * self.esc
        Y = (P @ self.v - self.vmin) * self.esc
        Z = -(P @ self.L)
        return X, Y, Z

    def amostra(self, X, Y):
        xi = np.clip(X.astype(np.int64), 0, self.n - 1)
        yi = np.clip(Y.astype(np.int64), 0, self.n - 1)
        v = self.mapa[yi, xi].astype(np.float32)
        fora = (X < 0) | (Y < 0) | (X >= self.n) | (Y >= self.n)
        v[fora] = np.inf
        return v


def disco_poisson(n, semente):
    rng = np.random.default_rng(semente)
    pts = []
    while len(pts) < n:
        p = rng.uniform(-1, 1, 2)
        if np.dot(p, p) <= 1 and all(np.linalg.norm(p - q) > 0.9 / math.sqrt(n) for q in pts):
            pts.append(p)
    return np.array(pts)


BUSCA = disco_poisson(10, 3)
PCF = disco_poisson(16, 5)


def sombra_pcss(mapa, P, N, ndl, idx_pix, ang=0.035):
    tx = mapa.texel
    Po = P + N * (1.5 * tx)
    X, Y, D = mapa.coords(Po)
    tg = np.sqrt(np.clip(1 - ndl ** 2, 0, 1)) / np.maximum(ndl, 0.05)
    bias = tx * (0.8 + 1.2 * np.minimum(tg, 4.0))
    rot = (np.sin(idx_pix * 12.9898 + 0.7) * 43758.5453) % 1.0 * 2 * np.pi
    c, s = np.cos(rot), np.sin(rot)
    rb = 7.0 / tx  # raio de busca de bloqueadores: 7 mm
    soma = np.zeros(len(P), np.float32)
    cont = np.zeros(len(P), np.float32)
    for dx, dy in BUSCA:
        ox, oy = (dx * c - dy * s) * rb, (dx * s + dy * c) * rb
        m = mapa.amostra(X + ox, Y + oy)
        blq = m < D - bias
        soma += np.where(blq, m, 0)
        cont += blq
    vis = np.ones(len(P), np.float32)
    tem = cont > 0
    if not tem.any():
        return vis
    Dt, Xt, Yt, bt = D[tem], X[tem], Y[tem], bias[tem]
    db = soma[tem] / cont[tem]
    pen = np.clip((Dt - db) * ang / tx, 1.2, 30.0)
    ct, st = c[tem], s[tem]
    acc = np.zeros(len(Dt), np.float32)
    for dx, dy in PCF:
        ox, oy = (dx * ct - dy * st) * pen, (dx * st + dy * ct) * pen
        acc += (Dt - bt <= mapa.amostra(Xt + ox, Yt + oy))
    vis[tem] = acc / len(PCF)
    return vis


def direcoes_ceu(n):
    dirs = []
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 0.18 + 0.82 * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        a = i * ga
        dirs.append((r * math.cos(a), r * math.sin(a), z))
    return np.array(dirs)


def visib_ceu(mapas, P, N):
    tot = np.zeros(len(P), np.float32)
    media = np.zeros(len(P), np.float32)
    norma = 0.0
    for mp in mapas:
        cosn = (N @ mp.L).astype(np.float32)
        Po = P + N * (2.0 * mp.texel)
        X, Y, D = mp.coords(Po)
        bias = 1.5 * mp.texel
        v = np.zeros(len(P), np.float32)
        for ox, oy in ((-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5)):
            v += (D - bias <= mp.amostra(X + ox, Y + oy))
        v *= 0.25
        tot += np.maximum(cosn, 0) * v
        media += v
        norma += max(mp.L[2], 0)
    return tot / norma, media / len(mapas)


# ----------------------------------------------------------------------
# Texturas e materiais procedurais
# ----------------------------------------------------------------------

class Textura:
    def __init__(self, arquivo):
        im = Image.open(TEX / arquivo).convert("RGBA")
        a = np.asarray(im, np.float32) / 255.0
        rgb = srgb_para_lin(a[..., :3])
        base = np.concatenate([rgb, a[..., 3:]], axis=2)
        self.niveis = [base]
        while min(self.niveis[-1].shape[:2]) > 8:
            h, w = self.niveis[-1].shape[:2]
            self.niveis.append(cv2.resize(self.niveis[-1], (max(w // 2, 1), max(h // 2, 1)), interpolation=cv2.INTER_AREA))

    def amostrar(self, u, v, lod):
        out = np.zeros((len(u), 4), np.float32)
        nivel = np.clip(np.round(lod), 0, len(self.niveis) - 1).astype(int)
        for k in np.unique(nivel):
            s = nivel == k
            img = self.niveis[k]
            h, w = img.shape[:2]
            x = np.clip(u[s], 0, 1) * w - 0.5
            y = (1 - np.clip(v[s], 0, 1)) * h - 0.5
            xf, yf = np.floor(x), np.floor(y)
            fx, fy = (x - xf)[:, None], (y - yf)[:, None]
            xa = np.clip(xf, 0, w - 1).astype(int)
            xb = np.clip(xf + 1, 0, w - 1).astype(int)
            ya = np.clip(yf, 0, h - 1).astype(int)
            yb = np.clip(yf + 1, 0, h - 1).astype(int)
            out[s] = ((img[ya, xa] * (1 - fx) + img[ya, xb] * fx) * (1 - fy) +
                      (img[yb, xa] * (1 - fx) + img[yb, xb] * fx) * fy)
        return out


def lod_uv(uv, idx, Wt, Ht, tam):
    """Nível de mipmap por pixel a partir da derivada de UV na tela."""
    lods = np.zeros(len(idx), np.float32)
    for k in range(2):
        img = np.full(Wt * Ht, np.nan, np.float32)
        img[idx] = uv[:, k] * tam[k]
        img = img.reshape(Ht, Wt)
        dx = np.fmin(np.abs(np.diff(img, axis=1, append=np.nan)), np.abs(np.diff(img, axis=1, prepend=np.nan)))
        dy = np.fmin(np.abs(np.diff(img, axis=0, append=np.nan)), np.abs(np.diff(img, axis=0, prepend=np.nan)))
        d = np.fmax(dx, dy).reshape(-1)[idx]
        lods = np.fmax(lods, np.nan_to_num(d, nan=1.0))
    return np.log2(np.maximum(lods, 1.0))


def proc_madeira(P):
    x, y = P[:, 0], P[:, 1]
    n = G.fbm2(x * 0.003, y * 0.03, 4)
    veio = 0.5 + 0.5 * np.sin(2 * np.pi * (y / 11.0 + 2.2 * n))
    veio = 0.65 * veio + 0.35 * (0.5 + 0.5 * G.fbm2(x * 0.01, y * 0.12, 3))
    fino = G.fbm2(x * 0.06, y * 0.9, 2)
    c1, c2 = lin("#D6B686"), lin("#E9D4AE")
    cor = c1 + (c2 - c1) * (veio ** 0.9)[:, None]
    cor *= (1 + 0.07 * fino)[:, None]
    tabua = np.floor(y / 140.0)
    tom = 1 + 0.07 * np.sin(tabua * 91.7 + 3.1)
    cor *= tom[:, None]
    fresta = ((y / 140.0) % 1.0) < 0.007
    cor[fresta] *= 0.55
    return cor.astype(np.float32)


def proc_terracota(P):
    n = G.fbm2(P[:, 0] * 0.12 + P[:, 2] * 0.09, P[:, 1] * 0.12 - P[:, 2] * 0.05, 4)
    f = G.ruido2(P[:, 0] * 1.7 + P[:, 2], P[:, 1] * 1.7)
    c1, c2 = lin("#A9502B"), lin("#C66C43")
    t = np.clip(0.5 + 0.6 * n + 0.08 * f, 0, 1)
    return (c1 + (c2 - c1) * t[:, None]).astype(np.float32)


def proc_terra(P):
    x, y = P[:, 0], P[:, 1]
    n = G.fbm2(x * 0.3, y * 0.3, 5)
    c1, c2 = lin("#1E140D"), lin("#5A4431")
    t = np.clip(0.5 + 0.75 * n, 0, 1)
    cor = c1 + (c2 - c1) * t[:, None]
    grao = G.ruido2(x * 2.3, y * 2.3)
    cor *= (0.75 + 0.25 * (grao * 0.5 + 0.5))[:, None]
    # perlita: pontinhos claros
    cx, cy = np.floor(x / 1.3), np.floor(y / 1.3)
    hsh = (np.sin(cx * 127.1 + cy * 311.7) * 43758.5453) % 1.0
    ox = (np.sin(cx * 269.5 + cy * 183.3) * 43758.5453) % 1.0
    oy = (np.sin(cx * 419.2 + cy * 371.9) * 43758.5453) % 1.0
    d = np.hypot(x / 1.3 - cx - ox * 0.6 - 0.2, y / 1.3 - cy - oy * 0.6 - 0.2)
    perl = (hsh > 0.9) & (d < 0.28)
    cor[perl] = lin("#E4DFD1")
    return cor.astype(np.float32)


# ----------------------------------------------------------------------
# Iluminação
# ----------------------------------------------------------------------

def normalizar(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


class Luz:
    def __init__(self, chave=(-0.55, -0.62, 0.86), e_chave=0.95, e_ceu=0.5, preench=(0.85, -0.25, 0.45),
                 e_preench=0.14, e_chao=0.10, ang=0.035):
        self.L = normalizar(np.array(chave, float))
        self.Lf = normalizar(np.array(preench, float))
        self.e_chave, self.e_ceu, self.e_preench, self.e_chao, self.ang = e_chave, e_ceu, e_preench, e_chao, ang


def ambiente(R, luz):
    z = R[:, 2:3]
    horiz, zen, chao = lin("#D9D3C8") * 0.75, lin("#F4F2EE") * 1.0, lin("#C9A982") * 0.30
    t = np.clip(z, 0, 1) ** 0.6
    ceu = horiz + (zen - horiz) * t
    cor = np.where(z > 0, ceu, chao + (horiz - chao) * np.clip(z + 1, 0, 1) ** 4)
    c = R @ luz.L
    caixa = np.clip((c - math.cos(math.radians(17))) / (math.cos(math.radians(9)) - math.cos(math.radians(17))), 0, 1)
    c2 = R @ luz.Lf
    faixa = np.clip((c2 - math.cos(math.radians(24))) / (math.cos(math.radians(14)) - math.cos(math.radians(24))), 0, 1)
    return cor + (4.0 * caixa ** 2 + 1.4 * faixa ** 2)[:, None]


def khronos_neutral(c):
    c = c.copy()
    x = c.min(axis=1)
    off = np.where(x < 0.08, x - 6.25 * x * x, 0.04)
    c -= off[:, None]
    pico = c.max(axis=1)
    ini = 0.8 - 0.04
    d = 1 - ini
    novo = 1 - d * d / (pico + d - ini)
    comp = pico >= ini
    escala = np.where(comp, novo / np.maximum(pico, 1e-6), 1.0)
    c *= escala[:, None]
    g = np.where(comp, 1 - 1 / (0.15 * (pico - novo) + 1), 0.0)
    c = c * (1 - g[:, None]) + novo[:, None] * g[:, None]
    return np.clip(c, 0, 1)


def para_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


# ----------------------------------------------------------------------
# Renderização de um tile
# ----------------------------------------------------------------------

class Render:
    def __init__(self, cena, cam_cfg, luz, ss=2, n_chave=3072, n_ceu=1024, n_dirs=20, fundo=None, exposicao=1.0):
        t0 = time.time()
        self.tri_all = Triangulos(cena)
        transp = np.array([MATS[NOMES[m]].get("transp", False) for m in self.tri_all.M])
        self.opaco = self.tri_all.subconjunto(~transp)
        self.agua = self.tri_all.subconjunto(self.tri_all.M == ID["agua"])
        self.mang = self.tri_all.subconjunto(self.tri_all.M == ID["mangueira"])
        proj = self.opaco.subconjunto(self.opaco.proj)
        print(f"triângulos: {len(self.tri_all.M)} ({time.time() - t0:.1f}s)", flush=True)
        self.ss = ss
        self.W, self.H = W_FINAL * ss, H_FINAL * ss
        self.cam = Camera(cam_cfg["pos"], cam_cfg["alvo"], cam_cfg["lente"], self.W, self.H)
        self.luz = luz
        self.fundo = fundo
        self.exposicao = exposicao
        t0 = time.time()
        self.chave = MapaSombra(luz.L, proj, n_chave)
        self.ceu = [MapaSombra(d, proj, n_ceu, meia=True) for d in direcoes_ceu(n_dirs)]
        print(f"mapas de sombra: {time.time() - t0:.1f}s", flush=True)
        self.tex = {}
        for n in NOMES:
            arq = MATS[n].get("tex")
            if arq:
                self.tex[n] = Textura(arq)

    def tile(self, ox, oy, Wt, Ht):
        cam = self.cam
        X, Y, Z = cam.projetar(self.opaco.P, ox, oy)
        zb, tb, b1, b2 = rasterizar(X, Y, Z, Wt, Ht)
        img = np.zeros((Wt * Ht, 3), np.float32)
        fundo_mask = tb < 0
        if self.fundo is not None:
            img[:] = self.fundo_px(ox, oy, Wt, Ht)
        idx = np.nonzero(~fundo_mask)[0]
        if len(idx):
            img[idx] = self.sombrear(self.opaco, idx, tb[idx], b1[idx], b2[idx], ox, oy, Wt, Ht)
        # camadas translúcidas: água, depois mangueira
        for camada, tipo in ((self.agua, "agua"), (self.mang, "mangueira")):
            if len(camada.M) == 0:
                continue
            X, Y, Z = cam.projetar(camada.P, ox, oy)
            zt, tt, c1, c2 = rasterizar(X, Y, Z, Wt, Ht)
            sel = np.nonzero((tt >= 0) & (zt < zb))[0]
            if len(sel):
                img[sel] = self.translucido(camada, tipo, sel, tt[sel], c1[sel], c2[sel], zt[sel], zb[sel], img[sel],
                                            ox, oy)
        return img

    def fundo_px(self, ox, oy, Wt, Ht):
        ys, xs = np.mgrid[0:Ht, 0:Wt]
        u = (xs + ox) / self.W - 0.5
        v = (ys + oy) / self.H - 0.42
        r = np.sqrt(u * u * 1.1 + v * v).reshape(-1)
        c0, c1 = lin(self.fundo[0]), lin(self.fundo[1])
        t = np.clip(r / 0.75, 0, 1)[:, None] ** 1.6
        return (c0 + (c1 - c0) * t).astype(np.float32)

    def pontos(self, tri, t, b1, b2):
        b0 = 1 - b1 - b2
        P = b0[:, None] * tri.P[t, 0] + b1[:, None] * tri.P[t, 1] + b2[:, None] * tri.P[t, 2]
        N = b0[:, None] * tri.N[t, 0] + b1[:, None] * tri.N[t, 1] + b2[:, None] * tri.N[t, 2]
        uv = b0[:, None] * tri.UV[t, 0] + b1[:, None] * tri.UV[t, 1] + b2[:, None] * tri.UV[t, 2]
        return P.astype(np.float64), normalizar(N.astype(np.float64)), uv

    def sombrear(self, tri, idx, t, b1, b2, ox, oy, Wt, Ht):
        luz = self.luz
        P, N, uv = self.pontos(tri, t, b1, b2)
        V = normalizar(self.cam.pos - P)
        vira = (N * V).sum(1) < 0
        N[vira] *= -1
        mat = tri.M[t].astype(np.int64)
        alb = PAL[mat].copy()
        ks, sh, f0, envk, emis = KS[mat].copy(), SH[mat], F0[mat].copy(), ENV[mat].copy(), EMIS[mat]
        metal = METAL[mat]
        emissao = np.zeros_like(alb)
        for nome, tx in self.tex.items():
            s = mat == ID[nome]
            if not s.any():
                continue
            h0, w0 = tx.niveis[0].shape[:2]
            lod = lod_uv(uv[s], idx[s], Wt, Ht, (w0, h0))
            amos = tx.amostrar(uv[s, 0], uv[s, 1], lod)
            if MATS[nome].get("emis"):
                emissao[s] = amos[:, :3] * MATS[nome]["emis"]
            else:
                alb[s] = amos[:, :3]
            if nome == "tampo":
                mm = amos[:, 3]
                f0[s] = 0.04 + 0.4 * mm
                envk[s] = 0.25 + 0.4 * mm
                ks[s] = 0.15 + 0.3 * mm
        for nome, fn in (("madeira", proc_madeira), ("terracota", proc_terracota), ("terra", proc_terra)):
            s = mat == ID[nome]
            if s.any():
                alb[s] = fn(P[s])
        ndl = np.clip(N @ luz.L, 0, 1)
        vis = np.ones(len(P), np.float32)
        acesa = ndl > 0
        if acesa.any():
            vis[acesa] = sombra_pcss(self.chave, P[acesa], N[acesa], ndl[acesa], idx[acesa] + ox * 7 + oy * 13,
                                     luz.ang)
        ceu, ceu_m = visib_ceu(self.ceu, P, N)
        luz_dif = (luz.e_chave * ndl * vis + luz.e_ceu * ceu + luz.e_preench * np.clip(N @ luz.Lf, 0, 1)
                   + luz.e_chao * (1 - N[:, 2]) * 0.5 * (0.4 + 0.6 * ceu_m))
        Hh = normalizar(luz.L[None, :] + V)
        nh = np.clip((N * Hh).sum(1), 0, 1)
        espec = ks * nh ** sh * ndl * vis * luz.e_chave * 1.6
        ndv = np.clip((N * V).sum(1), 0, 1)
        Fr = f0 + (1 - f0) * (1 - ndv) ** 5
        R = 2 * ndv[:, None] * N - V
        env = ambiente(R, luz) * (0.3 + 0.7 * ceu_m)[:, None]
        kd = np.where(metal, 0.12, 1.0)[:, None]
        tinte = np.where(metal[:, None], alb, 1.0)
        cor = (alb * luz_dif[:, None] * kd * (1 - (Fr * envk)[:, None])
               + espec[:, None] * tinte + (Fr * envk)[:, None] * env * tinte + emissao)
        # piso da vista explodida: só escurece o fundo onde há sombra
        s = mat == ID["piso"]
        if s.any():
            livre = luz.e_chave * ndl[s] + luz.e_ceu + luz.e_preench * np.clip(N[s] @ luz.Lf, 0, 1)
            fator = np.clip(luz_dif[s] / livre, 0, 1)
            base = self.fundo_px(ox, oy, Wt, Ht)[idx[s]]
            cor[s] = base * (1 - 0.62 * (1 - fator[:, None]))
        return (cor * self.exposicao).astype(np.float32)

    def translucido(self, tri, tipo, idx, t, b1, b2, zt, zo, atras, ox, oy):
        luz = self.luz
        P, N, uv = self.pontos(tri, t, b1, b2)
        V = normalizar(self.cam.pos - P)
        vira = (N * V).sum(1) < 0
        N[vira] *= -1
        ndl = np.clip(N @ luz.L, 0, 1)
        Hh = normalizar(luz.L[None, :] + V)
        nh = np.clip((N * Hh).sum(1), 0, 1)
        ndv = np.clip((N * V).sum(1), 0, 1)
        R = 2 * ndv[:, None] * N - V
        if tipo == "agua":
            # ondulação leve na superfície
            gx = G.ruido2(P[:, 0] * 0.08 + 5.0, P[:, 1] * 0.08) * 0.05
            gy = G.ruido2(P[:, 0] * 0.08, P[:, 1] * 0.08 + 9.0) * 0.05
            Nw = normalizar(np.c_[gx, gy, np.ones(len(P))])
            ndv = np.clip((Nw * V).sum(1), 0, 1)
            R = 2 * ndv[:, None] * Nw - V
            nh = np.clip((Nw * Hh).sum(1), 0, 1)
            esp = np.minimum(zo - zt, 400.0)
            abs_ = 0.30 + 0.45 * (1 - np.exp(-esp * 0.03))
            tint = lin("#2E86C1") * 0.50
            filtro = np.array([0.78, 0.92, 1.0], np.float32)
            Fr = 0.03 + 0.97 * (1 - ndv) ** 5
            cor = atras * filtro * (1 - abs_[:, None]) + tint * abs_[:, None]
            cor = cor * (1 - Fr[:, None]) + Fr[:, None] * ambiente(R, luz) * 1.1
            cor += (1.2 * nh ** 300 * luz.e_chave)[:, None]
        else:
            a = 0.16 + 0.6 * (1 - ndv) ** 2
            base = lin(MATS["mangueira"]["cor"]) * (0.35 + 0.65 * ndl[:, None] * luz.e_chave)
            Fr = 0.04 + 0.96 * (1 - ndv) ** 5
            cor = atras * (1 - a[:, None]) + base * a[:, None]
            cor = cor * (1 - 0.5 * Fr[:, None]) + 0.5 * Fr[:, None] * ambiente(R, luz)
            cor += (0.9 * nh ** 140 * ndl * luz.e_chave)[:, None]
        return cor.astype(np.float32)

    def renderizar(self, tw=960, th=1080):
        ss = self.ss
        saida = np.zeros((H_FINAL, W_FINAL, 3), np.uint8)
        t0 = time.time()
        for oy in range(0, self.H, th):
            for ox in range(0, self.W, tw):
                Wt, Ht = min(tw, self.W - ox), min(th, self.H - oy)
                lin_img = self.tile(ox, oy, Wt, Ht)
                srgb = para_srgb(khronos_neutral(lin_img)).reshape(Ht, Wt, 3).astype(np.float32)
                if ss > 1:
                    srgb = cv2.resize(srgb, (Wt // ss, Ht // ss), interpolation=cv2.INTER_AREA)
                y0, x0 = oy // ss, ox // ss
                saida[y0:y0 + srgb.shape[0], x0:x0 + srgb.shape[1]] = np.clip(srgb * 255 + 0.5, 0, 255).astype(np.uint8)
                print(f"  tile ({ox},{oy}) {time.time() - t0:.0f}s", flush=True)
        return saida

    def projetar_final(self, p):
        x, y, z = self.cam.projetar(np.asarray(p, float)[None, :])
        return float(x[0]) / self.ss, float(y[0]) / self.ss


# ----------------------------------------------------------------------
# Cenas: câmera, luz e pós-processamento
# ----------------------------------------------------------------------

CENAS = {
    "hero": dict(arquivo="sit_hero.png", cam=dict(pos=(300, -700, 400), alvo=(-10, 40, 75), lente=38)),
    "closeup": dict(arquivo="sit_estacao_closeup.png", cam=dict(pos=(430, -470, 330), alvo=(140, -5, 50), lente=50)),
    "interno": dict(arquivo="sit_interno.png", cam=dict(pos=(90, -110, 420), alvo=(88, 40, 5), lente=45)),
    "explodida": dict(arquivo="sit_explodida.png", cam=dict(pos=(580, -610, 520), alvo=(140, 15, 95), lente=46),
                      fundo=("#FBF6E6", "#EFE6CC")),
    "sobre_notebook": dict(arquivo="sit_sobre_notebook.png",
                           cam=dict(pos=(520, -640, 470), alvo=(105, 15, 40), lente=56)),
}

ROTULOS_DESLOC = {  # deslocamento do texto em relação ao ponto (px na imagem final) e alinhamento
    "Tampa com sensor AM2302": (-190, -45, "dir"),
    "Caixa da eletrônica (ESP32-S3)": (-190, -15, "dir"),
    "Reservatório com bomba": (-115, 50, "dir"),
    "Coroa do vaso": (150, -55, "esq"),
    "Vaso com terra": (150, 45, "esq"),
}


def rotular(img, r, rotulos):
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("C:/Windows/Fonts/seguisb.ttf", 30)
    except OSError:
        f = ImageFont.load_default()
    tinta = (30, 27, 22)
    for nome, p in rotulos.items():
        x, y = r.projetar_final(p)
        dx, dy, al = ROTULOS_DESLOC.get(nome, (150, -50, "esq"))
        tx, ty = x + dx, y + dy
        d.line([(x, y), (tx + (12 if al == "dir" else -12), ty)], fill=tinta, width=2)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=tinta)
        anc = "rm" if al == "dir" else "lm"
        d.text((tx, ty), nome, font=f, fill=tinta, anchor=anc)
    return np.asarray(im)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cena", default="hero", choices=list(CENAS))
    ap.add_argument("--previa", action="store_true")
    ap.add_argument("--ss", type=int, default=2)
    ap.add_argument("--saida", default=None)
    ap.add_argument("--sem-rotulos", action="store_true")
    a = ap.parse_args()
    cfg = CENAS[a.cena]
    t0 = time.time()
    cena = G.MONTAGENS[a.cena]()
    luz = Luz()
    if a.previa:
        r = Render(cena, cfg["cam"], luz, ss=1, n_chave=2048, n_ceu=512, n_dirs=12, fundo=cfg.get("fundo"))
        img = r.renderizar(tw=1920, th=540)
    else:
        r = Render(cena, cfg["cam"], luz, ss=a.ss, fundo=cfg.get("fundo"))
        img = r.renderizar(tw=960 if a.ss > 1 else 1920, th=1080 if a.ss > 1 else 540)
    if cena.rotulos and not a.sem_rotulos:
        img = rotular(img, r, cena.rotulos)
    saida = Path(a.saida) if a.saida else SAIDA / cfg["arquivo"]
    saida.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img).save(saida, compress_level=6)
    print(f"SALVO: {saida} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
