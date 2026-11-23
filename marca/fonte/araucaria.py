"""Gera a silhueta de uma araucária (Araucaria angustifolia adulta) como um único caminho SVG.

Tronco alto e reto, galhos só no alto, saindo em verticilos e subindo em curva (candelabro),
e tufos de folhagem densos e voltados para cima nas pontas, formando a copa em taça de topo plano.
Origem na base do tronco; altura total ~100. Rodar: python araucaria.py [semente]
"""
import math
import random
import sys


def bezier(p0, p1, p2, t):
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def tracar(p0, p1, p2, w0, w1, n=14):
    """Galho ou tronco: curva quadrática engrossada, afinando de w0 para w1. Retorna polígono."""
    esq, dir_ = [], []
    for k in range(n + 1):
        t = k / n
        x, y = bezier(p0, p1, p2, t)
        x2, y2 = bezier(p0, p1, p2, min(t + 0.01, 1))
        x1, y1 = bezier(p0, p1, p2, max(t - 0.01, 0))
        dx, dy = x2 - x1, y2 - y1
        nrm = math.hypot(dx, dy) or 1
        nx, ny = -dy / nrm, dx / nrm
        w = (w0 + (w1 - w0) * t) / 2
        esq.append((x + nx * w, y + ny * w))
        dir_.append((x - nx * w, y - ny * w))
    return esq + dir_[::-1]


def tufo(rng, cx, cy, largura, altura, inclina=0.0):
    """Tufo de folhagem em forma de pincel virado para cima: base estreita, topo largo e espetado."""
    pts = []
    base = (cx, cy + altura * 0.35)
    pts.append(base)
    n = 22
    for k in range(n + 1):
        a = math.pi + math.pi * k / n  # de 180 a 360 graus: meia-lua de cima
        r_x = largura / 2 * (1 + rng.uniform(-0.08, 0.08))
        r_y = altura * (0.55 + 0.45 * math.sin(math.pi * k / n))
        espinho = rng.uniform(0.0, 0.16) if k % 2 else 0
        x = cx + math.cos(a) * r_x * (1 + espinho * 0.4) + inclina * (1 - math.cos(math.pi * k / n)) * 0.0
        y = cy + math.sin(a) * r_y * (1 + espinho)
        pts.append((x, y))
    pts.append(base)
    return pts


def araucaria(semente=7):
    rng = random.Random(semente)
    formas = []
    topo = -74
    # tronco levemente afunilado
    formas.append(tracar((0, 0), (rng.uniform(-0.6, 0.6), -40), (0, topo), 5.0, 2.2))
    # tocos de galhos secos no tronco
    for y in (-30, -40, -48):
        lado = rng.choice((-1, 1))
        formas.append(tracar((0, y), (lado * 4, y - 1), (lado * 7, y - 4), 1.8, 0.6, 6))
    # galhos do candelabro: saem de alturas diferentes do alto do tronco (os de fora mais baixo),
    # vão primeiro para o lado e depois sobem até o topo da copa. Assimétricos de propósito.
    n_galhos = rng.randint(8, 10)
    fracs = sorted(rng.uniform(-1, 1) for _ in range(n_galhos))
    fracs[0], fracs[-1] = -rng.uniform(0.9, 1.05), rng.uniform(0.9, 1.05)
    for frac in fracs:
        y0 = -72 + abs(frac) * rng.uniform(12, 20)
        alcance = 33 * frac * rng.uniform(0.85, 1.1)
        y_ponta = -86 - rng.uniform(0, 7) + abs(frac) * 3
        meio = (alcance * rng.uniform(0.8, 1.0), y0 - rng.uniform(0, 3))
        ponta = (alcance + frac * rng.uniform(0, 3), y_ponta)
        formas.append(tracar((0, y0), meio, ponta, 3.4, 1.8, 18))
        formas.append(tufo(rng, ponta[0], ponta[1], rng.uniform(15, 22), rng.uniform(6.5, 9.5)))
        if abs(frac) > 0.45 and rng.random() < 0.7:
            x2, y2 = bezier((0, y0), meio, ponta, rng.uniform(0.6, 0.78))
            formas.append(tufo(rng, x2, y2 - 1, rng.uniform(10, 14), rng.uniform(4.5, 6.5)))
    return formas


def caminhos(formas):
    """Um caminho por forma: sobrepor formas separadas não abre frestas, ao contrário de juntar num path só."""
    return ["M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in f) + "Z" for f in formas]


if __name__ == "__main__":
    semente = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    sys.stdout.write("\n".join(caminhos(araucaria(semente))))
