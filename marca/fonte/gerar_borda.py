"""Gera app/src/components/BordaRS.vue: a borda de baixo dos cabeçalhos do app.

A borda é um trecho real da divisa norte do RS (rios Uruguai e Pelotas, divisa com Santa Catarina),
tirado do contorno do estado no OpenStreetMap (divisa-rs.json, ODbL) e simplificado. Sobre ela ficam
três araucárias geradas por araucaria.py.

Rodar da raiz do repositório:  python3 marca/fonte/gerar_borda.py

Para atualizar divisa-rs.json (anel externo do RS, lon/lat), no container da API:
    osmium getid -r /dados/osm/sul-latest.osm.pbf r242620 -o rs.osm.pbf
    osmium export rs.osm.pbf -f geojson --geometry-types=polygon -o rs.geojson
e simplificar o polígono "Rio Grande do Sul" com tolerância 0.004 grau.
"""
import json
import math
from pathlib import Path

from araucaria import araucaria, caminhos

PASTA = Path(__file__).parent
SAIDA = PASTA.parent.parent / "app" / "src" / "components" / "BordaRS.vue"
SAIDA_ABAS = PASTA.parent.parent / "app" / "src" / "components" / "BordaAbas.vue"

LARGURA = 390  # largura de referência (celular); em telas maiores o desenho se repete para a esquerda
JANELA = (-52.3, -50.3)  # longitudes do trecho da divisa (cabeçalho)
JANELA_ABAS = (-55.2, -53.0)  # outro trecho, mais a oeste, para a barra de abas
TOLERANCIA = 0.025  # grau: simplifica os meandros dos rios para virar uma linha de mapa
AMPLITUDE, BASE = 18, 6  # px: variação vertical da borda e onde ela começa
# (semente, x, escala): três araucárias no canto direito
ARVORES = [(11, 296, 0.56), (7, 336, 0.74), (23, 372, 0.5)]


def divisa_norte(anel):
    """Divisa norte inteira: do extremo oeste ao extremo leste passando pelo ponto mais ao norte."""
    if anel[0] == anel[-1]:
        anel = anel[:-1]
    n = len(anel)
    norte = max(range(n), key=lambda i: anel[i][1])
    oeste = min(range(n), key=lambda i: anel[i][0])
    leste = max(range(n), key=lambda i: anel[i][0])

    def caminhar(de, ate, passo):
        pts, i = [anel[de]], de
        while i != ate:
            i = (i + passo) % n
            pts.append(anel[i])
        return pts

    for passo in (1, -1):
        lado_oeste = caminhar(norte, oeste, passo)
        if len(lado_oeste) < n // 2:
            lado_leste = caminhar(norte, leste, -passo)
            break
    return list(reversed(lado_oeste)) + lado_leste[1:]


def simplificar(pts, tol):
    """Douglas-Peucker."""
    if len(pts) < 3:
        return pts
    (ax, ay), (bx, by) = pts[0], pts[-1]
    dx, dy = bx - ax, by - ay
    norma = math.hypot(dx, dy) or 1e-12
    dist = [abs(dy * x - dx * y + bx * ay - by * ax) / norma for x, y in pts]
    k = max(range(len(pts)), key=dist.__getitem__)
    if dist[k] <= tol:
        return [pts[0], pts[-1]]
    return simplificar(pts[: k + 1], tol)[:-1] + simplificar(pts[k:], tol)


def borda(anel, janela=JANELA, amplitude=AMPLITUDE, base=BASE):
    l1, l2 = janela
    pts = simplificar([p for p in divisa_norte(anel) if l1 <= p[0] <= l2], TOLERANCIA)
    monotono = [pts[0]]  # sem ganchos: a borda só avança para a direita
    for p in pts[1:]:
        if p[0] > monotono[-1][0]:
            monotono.append(p)
    (x0, y0), (x1, y1) = monotono[0], monotono[-1]
    dados = []
    for lon, lat in monotono:  # tira a inclinação geral: as pontas ficam na mesma altura e o desenho emenda
        t = (lon - x0) / (x1 - x0)
        dados.append((t * LARGURA, -(lat - (y0 + (y1 - y0) * t))))
    lo, hi = min(y for _, y in dados), max(y for _, y in dados)
    esc = amplitude / (hi - lo)
    return [(x, base + (y - lo) * esc) for x, y in dados]


def altura_em(pts, x):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x1 <= x <= x2:
            return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    return pts[-1][1]


def main():
    anel = json.loads((PASTA / "divisa-rs.json").read_text())
    pts = borda(anel)
    faixa = f"M0 0H{LARGURA}V{pts[-1][1]:.1f}" + "".join(f"L{x:.1f} {y:.1f}" for x, y in reversed(pts)) + "Z"

    arvores = []
    for semente, x, escala in ARVORES:
        corpo = "".join(f'<path d="{d}" />' for d in caminhos(araucaria(semente)))
        arvores.append(f'<g transform="translate({x} {altura_em(pts, x) + 2:.1f}) scale({escala})">{corpo}</g>')

    copias = "\n      ".join(
        f'<path transform="translate({-LARGURA * k} 0)" d="{faixa}" />' if k else f'<path d="{faixa}" />'
        for k in range(4)
    )
    SAIDA.write_text(f"""<template>
  <!--
    Gerado por marca/fonte/gerar_borda.py. Não editar à mão.
    Borda dos cabeçalhos: um trecho real da divisa norte do RS (OpenStreetMap, ODbL) com três araucárias.
    O desenho tem {LARGURA} px de largura e fica ancorado à direita; em telas maiores ele se repete para a esquerda.
  -->
  <svg class="borda-rs" viewBox="0 0 {LARGURA} 32" preserveAspectRatio="xMaxYMin meet" aria-hidden="true">
    <g class="borda-rs__faixa">
      {copias}
    </g>
    <g v-if="arvores" class="borda-rs__arvores">
      {"".join(arvores)}
    </g>
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{{ arvores?: boolean }}>(), {{ arvores: true }})
</script>

<style scoped>
.borda-rs {{
  display: block;
  width: 100%;
  height: 32px;
  overflow: visible;
}}

.borda-rs__faixa {{
  fill: var(--chasque-faixa);
}}

/* as araucárias são recortes na cor do vale, contra o céu da faixa */
.borda-rs__arvores {{
  fill: var(--chasque-fundo);
}}
</style>
""")
    print(f"{SAIDA}: {len(pts)} pontos na borda, {len(ARVORES)} araucárias, {SAIDA.stat().st_size // 1024} KB")

    # Barra de abas: a faixa sobe do rodapé e a borda de cima é a divisa, de cabeça para baixo.
    abas = borda(anel, JANELA_ABAS, amplitude=12, base=2)
    topo = f"M0 18V{18 - abas[0][1]:.1f}" + "".join(f"L{x:.1f} {18 - y:.1f}" for x, y in abas) + f"V18Z"
    copias_abas = "\n    ".join(
        f'<path transform="translate({-LARGURA * k} 0)" d="{topo}" />' if k else f'<path d="{topo}" />' for k in range(4)
    )
    SAIDA_ABAS.write_text(f"""<template>
  <!-- Gerado por marca/fonte/gerar_borda.py. Borda de cima da barra de abas: outro trecho da divisa do RS. -->
  <svg class="borda-abas" viewBox="0 0 {LARGURA} 18" preserveAspectRatio="xMaxYMax meet" aria-hidden="true">
    {copias_abas}
  </svg>
</template>

<style scoped>
.borda-abas {{
  display: block;
  width: 100%;
  height: 18px;
  overflow: visible;
  fill: var(--chasque-faixa);
}}
</style>
""")
    print(f"{SAIDA_ABAS}: {len(abas)} pontos")


if __name__ == "__main__":
    main()
