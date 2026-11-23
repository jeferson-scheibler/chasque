"""Cena da tela de entrada: a ruína da igreja de São Miguel Arcanjo (Missões, RS) em silhueta, contra a luz
de um sol baixo atrás da torre, com araucárias e o chão escuros, e o céu esquentando em ocre no horizonte.

Os vãos da ruína (arcos, janela, óculos, sineira) são furos: por eles aparece a luz do céu, como numa foto
contra o sol. Animação discreta: o sol sobe e o brilho cresce.

Gera app/src/components/CenaMissoes.vue. Rodar da raiz:  python3 marca/fonte/gerar_cena.py [--previa saida.svg]
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from araucaria import araucaria, caminhos  # noqa: E402
from gerar_borda import divisa_norte, simplificar  # noqa: E402

PASTA = Path(__file__).parent
SAIDA = PASTA.parent.parent / "app" / "src" / "components" / "CenaMissoes.vue"
L, A = 390, 300
CHAO = 214  # base da ruína no desenho original (antes de assentar na divisa)
ALICERCE = 70  # px que as paredes descem para dentro da colina: sem fresta de céu onde o chão é curvo
ALTURA_DIVISA = 62  # px: quanto a divisa sobe do extremo oeste até o ponto mais ao norte
TOPO_DIVISA = 182  # y do ponto mais ao norte do RS na cena


def arco(x1, x2, y_base):
    """Vão em arco pleno que nasce no chão (furo)."""
    r = (x2 - x1) / 2
    return f"M{x1} {CHAO + 1}V{y_base}A{r} {r} 0 0 1 {x2} {y_base}V{CHAO + 1}Z"


def arco_alto(x1, x2, y_base, y_peitoril):
    r = (x2 - x1) / 2
    return f"M{x1} {y_peitoril}V{y_base}A{r} {r} 0 0 1 {x2} {y_base}V{y_peitoril}Z"


def circulo(cx, cy, r):
    return f"M{cx - r} {cy}a{r} {r} 0 1 0 {2 * r} 0a{r} {r} 0 1 0 {-2 * r} 0Z"


def contorno_irregular(rng, pontos, amplitude=1.2):
    """Pequenas irregularidades nas arestas: pedra gasta, não régua."""
    saida = [(x + rng.uniform(-amplitude, amplitude) * 0.4, y + rng.uniform(-amplitude, amplitude)) for x, y in pontos]
    return "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in saida)


def ruina():
    """Silhueta da igreja de São Miguel: lista de (caminho, tem_furos). Furos usam fill-rule evenodd."""
    rng = random.Random(4)
    formas = []

    # fachada com frontão e volutas, quebrada nos cantos de cima
    topo = [(118, CHAO + ALICERCE), (118, 133), (123, 128), (127, 131), (133, 124), (146, 124), (149, 119), (152, 114),
            (156, 112), (170, 112), (185, 95), (200, 112), (207, 112), (210, 115), (213, 113), (216, 117),
            (219, 121), (224, 124), (234, 124), (238, 128), (243, 125), (247, 130), (252, 128), (252, CHAO + ALICERCE)]
    furos = [
        arco(124, 142, 186), arco(148, 166, 186), arco(171, 199, 182), arco(204, 222, 186), arco(228, 246, 186),
        arco_alto(178, 192, 138, 152), circulo(167.5, 146, 3.6), circulo(202.5, 146, 3.6),
        "M176 112a9 9 0 0 1 18 0Z",  # vão no frontão
        "M236 142l5 -3l3 6l-4 4l-5 -2Z",  # brecha na parede
    ]
    formas.append((contorno_irregular(rng, topo) + "Z " + " ".join(furos), True))
    formas.append(("M112 156H258V160.5H112Z", False))  # cornija saliente
    formas.append(("M184 79h2.2v16h-2.2zM179 84h12v2.2h-12z", False))  # cruz do frontão

    # torre do sino, quebrada no alto à direita
    torre = contorno_irregular(
        rng, [(258, CHAO + ALICERCE), (258, 78), (284, 78), (287, 83), (289, 82), (292, 88), (292, CHAO + ALICERCE)]
    )
    furos_torre = [arco_alto(266, 284, 94, 106), arco_alto(266, 284, 128, 141), "M276 170l4 -3l3 5l-3 3Z"]
    formas.append((torre + "Z " + " ".join(furos_torre), True))
    formas.append(("M256 149H294V152H256ZM256 111H294V114H256Z", False))  # frisos da torre
    formas.append(("M260 79C261 63 289 63 290 79Z", False))  # cúpula
    formas.append(("M271 65h8v-5h-8zM274 60h2v-11h-2zM270.5 53h9v2h-9z", False))  # lanterna e cruz

    # mato que cresce na ruína e entulho na base
    for x, y in ((128, 126), (238, 126), (289, 84)):
        formas.append((f"M{x - 4} {y + 1}l1.5 -5l1 4l1.5 -7l1 6l1.5 -4l1 5Z", False))
    return formas


def linha_da_divisa():
    """A divisa norte inteira do RS (do extremo oeste a Torres), com a inclinação real: o 'telhado' do mapa."""
    anel = json.loads((PASTA / "divisa-rs.json").read_text())
    pts = simplificar(divisa_norte(anel), 0.03)
    mono = [pts[0]]
    for p in pts[1:]:
        if p[0] > mono[-1][0]:
            mono.append(p)
    lon0, lon1 = mono[0][0], mono[-1][0]
    lat_max = max(lat for _, lat in mono)
    lat_min = min(lat for _, lat in mono)
    k = ALTURA_DIVISA / (lat_max - lat_min)
    return [((lon - lon0) / (lon1 - lon0) * L, TOPO_DIVISA + (lat_max - lat) * k) for lon, lat in mono]


def main():
    divisa = linha_da_divisa()

    def chao_em(x):
        for (x1, y1), (x2, y2) in zip(divisa, divisa[1:]):
            if x1 <= x <= x2:
                return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
        return divisa[-1][1]

    # chão escuro com o contorno do RS por cima, que se desfaz em degradê até a cor do formulário
    chao = f"M0 {A + 2}V{divisa[0][1]:.1f}" + "".join(f"L{x:.1f} {y:.1f}" for x, y in divisa) + f"V{A + 2}Z"
    # tudo o que está acima do chão: recorta prédio e árvores rente à linha da divisa (sem alicerce aparecendo na névoa)
    acima = f"M-20 -60H{L + 20}V{divisa[-1][1] + 1.5:.1f}" + "".join(
        f"L{x:.1f} {y + 1.5:.1f}" for x, y in reversed(divisa)
    ) + f"L-20 {divisa[0][1] + 1.5:.1f}Z"
    inicio_nevoa = max(y for _, y in divisa)  # a névoa só começa abaixo do ponto mais baixo da colina
    # A ruína se apoia no ponto mais alto do chão embaixo dela; onde a colina desce, o alicerce preenche.
    dy = min(chao_em(x) for x in range(118, 293, 2)) - CHAO + 2

    # moitas e pedras soltas apoiadas no chão onde estão
    def moita(x, largura, altura):
        y = chao_em(x + largura / 2) + 2
        return (f"M{x} {y:.1f}c{largura * 0.2:.1f} {-altura:.1f} {largura * 0.55:.1f} {-altura * 1.1:.1f} "
                f"{largura * 0.7:.1f} {-altura * 0.45:.1f}c{largura * 0.12:.1f} {-altura * 0.4:.1f} "
                f"{largura * 0.3:.1f} {-altura * 0.3:.1f} {largura * 0.3:.1f} {altura * 0.45 + 2:.1f}Z")

    entulho = "".join(f'<path d="{moita(x, w, h)}"/>' for x, w, h in ((96, 26, 9), (293, 24, 7), (150, 10, 3), (212, 9, 3)))

    arvores_longe, arvores_perto = [], []
    for semente, x, escala, perto in ((5, 22, 0.55, False), (11, 58, 0.82, True), (23, 92, 0.5, False),
                                       (13, 322, 0.58, False), (7, 350, 0.9, True), (19, 380, 0.62, True)):
        corpo = "".join(f'<path d="{d}"/>' for d in caminhos(araucaria(semente)))
        g = f'<g transform="translate({x} {chao_em(x) + (3 if perto else -1):.1f}) scale({escala})">{corpo}</g>'
        (arvores_perto if perto else arvores_longe).append(g)

    ruina_svg = "".join(
        f'<path fill-rule="evenodd" d="{d}"/>' if furos else f'<path d="{d}"/>' for d, furos in ruina()
    )

    corpo = f"""<defs>
      <clipPath id="cena-acima-do-chao"><path d="{acima}"/></clipPath>
      <linearGradient id="cena-chao-escuro" gradientUnits="userSpaceOnUse" x1="0" y1="{inicio_nevoa:.1f}" x2="0" y2="{A}">
        <stop offset="0" stop-color="var(--silhueta)"/>
        <stop offset="1" stop-color="var(--silhueta)"/>
      </linearGradient>
      <linearGradient id="cena-chao-claro" gradientUnits="userSpaceOnUse" x1="0" y1="{inicio_nevoa:.1f}" x2="0" y2="{A}">
        <stop offset="0" stop-color="var(--colina-perto)" stop-opacity="0"/>
        <stop offset="0.25" stop-color="var(--colina-perto)" stop-opacity="0.08"/>
        <stop offset="0.5" stop-color="var(--colina-perto)" stop-opacity="0.32"/>
        <stop offset="0.75" stop-color="var(--colina-perto)" stop-opacity="0.68"/>
        <stop offset="0.9" stop-color="var(--colina-perto)" stop-opacity="0.9"/>
        <stop offset="1" stop-color="var(--colina-perto)" stop-opacity="1"/>
      </linearGradient>
      <linearGradient id="cena-ceu" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="var(--chasque-ocre)" stop-opacity="0"/>
        <stop offset="0.55" stop-color="var(--chasque-ocre)" stop-opacity="0.10"/>
        <stop offset="0.86" stop-color="var(--chasque-ocre)" stop-opacity="0.42"/>
      </linearGradient>
      <radialGradient id="cena-halo">
        <stop offset="0" stop-color="var(--chasque-ocre)" stop-opacity="0.75"/>
        <stop offset="0.35" stop-color="var(--chasque-ocre)" stop-opacity="0.28"/>
        <stop offset="1" stop-color="var(--chasque-ocre)" stop-opacity="0"/>
      </radialGradient>
    </defs>
    <rect class="cena__ceu" width="{L}" height="{A}" fill="url(#cena-ceu)"/>
    <g class="cena__sol" transform="translate(0 {dy:.1f})">
      <circle cx="304" cy="150" r="120" fill="url(#cena-halo)"/>
      <circle cx="304" cy="150" r="27" fill="var(--chasque-ocre)"/>
    </g>
    <g class="cena__longe" clip-path="url(#cena-acima-do-chao)">{"".join(arvores_longe)}</g>
    <g class="cena__silhueta" clip-path="url(#cena-acima-do-chao)">
      <g transform="translate(0 {dy:.1f})">{ruina_svg}</g>
      {entulho}
      {"".join(arvores_perto)}
    </g>
    <!-- chão: silhueta que vira névoa e termina na cor do formulário (duas camadas de opacidade, suave) -->
    <path d="{chao}" fill="url(#cena-chao-escuro)"/>
    <path d="{chao}" fill="url(#cena-chao-claro)"/>"""

    if "--previa" in sys.argv:
        destino = Path(sys.argv[sys.argv.index("--previa") + 1])
        previa = (corpo.replace("var(--chasque-ocre)", "#D99A2B").replace("var(--silhueta)", "#10172a")
                  .replace("var(--colina-perto)", "#FAF6EE"))
        destino.write_text(f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {L} {A}">
  <style>.cena__longe {{ fill: #2a3559; }} .cena__silhueta {{ fill: #10172a; }}</style>
  <rect width="{L}" height="{A}" fill="#1f2b4d"/>
  {previa}
</svg>""")
        print("prévia:", destino)
        return

    SAIDA.write_text(f"""<template>
  <!--
    Gerado por marca/fonte/gerar_cena.py. Não editar à mão.
    A ruína de São Miguel Arcanjo (Missões) em silhueta contra o sol baixo, com araucárias; o vale claro
    embaixo tem a borda de um trecho da divisa do RS. Pelos vãos da ruína passa a luz do céu.
  -->
  <svg class="missoes" viewBox="0 0 {L} {A}" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
    {corpo}
  </svg>
</template>

<style scoped>
.missoes {{
  display: block;
  width: 100%;
  height: 100%;
}}

/* silhueta mais escura que o céu; ao fundo, araucárias um tom mais claras (distância) */
.missoes {{
  --silhueta: #10172a;
}}

.cena__silhueta {{
  fill: var(--silhueta);
}}

.cena__longe {{
  fill: #2a3559;
}}

@media (prefers-color-scheme: dark) {{
  .missoes {{
    --silhueta: #070b16;
  }}

  .cena__longe {{
    fill: #1c2643;
  }}
}}

/* o único movimento: o sol sobe atrás da torre e o céu esquenta */
.cena__sol {{
  animation: cena-nascer 1.8s cubic-bezier(0.16, 0.8, 0.24, 1) both;
}}

.cena__ceu {{
  animation: cena-aquecer 1.8s ease-out both;
}}

@keyframes cena-nascer {{
  from {{
    transform: translateY(46px);
  }}
}}

@keyframes cena-aquecer {{
  from {{
    opacity: 0.2;
  }}
}}

@media (prefers-reduced-motion: reduce) {{
  .cena__sol,
  .cena__ceu {{
    animation: none;
  }}
}}
</style>
""")
    print(f"{SAIDA} ({SAIDA.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
