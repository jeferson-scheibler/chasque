"""Escreve a tela de abertura animada dentro de app/index.html, entre os marcadores ABERTURA.

O contorno do símbolo se desenha em creme, preenche, o sol ocre acende e o nome aparece.
Fica no HTML (e não num componente) para aparecer no primeiro quadro, antes do JavaScript.
O app tira a abertura em src/main.ts. Rodar da raiz do repositório:
    python3 marca/fonte/gerar_abertura.py
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SIMBOLO = (RAIZ / "marca" / "simbolo-claro.svg").read_text()
NOME = (RAIZ / "marca" / "chasque-nome-claro.svg").read_text()
INDEX = RAIZ / "app" / "index.html"

CREME, OCRE, NOITE = "#FAF6EE", "#E3AE4E", "#1f2b4d"


def caminhos(svg):
    return re.findall(r'<path fill="([^"]+)" d="([^"]+)"', svg)


def caixa(svg):
    return re.search(r'viewBox="([^"]+)"', svg).group(1)


simbolo = "".join(
    f'<path class="{"a-sol" if cor.upper() == OCRE else "a-base"}" pathLength="1" d="{d}"/>'
    for cor, d in caminhos(SIMBOLO)
)
nome = "".join(f'<path d="{d}"/>' for _, d in caminhos(NOME))

estilo = f"""<style id="abertura-estilo">
      #abertura {{ position: fixed; inset: 0; z-index: 99999; display: flex; flex-direction: column; align-items: center;
        justify-content: center; gap: 30px; background: {NOITE}; transition: opacity .45s ease, visibility .45s; }}
      #abertura.saindo {{ opacity: 0; visibility: hidden; }}
      #abertura svg {{ display: block; overflow: visible; }}
      .abertura__simbolo {{ width: 150px; }}
      .abertura__nome {{ width: 168px; fill: {CREME}; opacity: 0; transform: translateY(8px);
        animation: abertura-surgir .6s 1.15s ease-out forwards; }}
      .abertura__simbolo path {{ fill: transparent; stroke-width: 2px; vector-effect: non-scaling-stroke;
        stroke-dasharray: 1; stroke-dashoffset: 1; stroke-linejoin: round; }}
      .abertura__simbolo .a-base {{ stroke: {CREME};
        animation: abertura-desenhar 1.1s cubic-bezier(.45,0,.2,1) forwards, abertura-creme .5s 1s ease forwards; }}
      .abertura__simbolo .a-sol {{ stroke: {OCRE};
        animation: abertura-desenhar .7s .55s cubic-bezier(.45,0,.2,1) forwards, abertura-ocre .5s 1.05s ease forwards; }}
      @keyframes abertura-desenhar {{ to {{ stroke-dashoffset: 0; }} }}
      @keyframes abertura-creme {{ to {{ fill: {CREME}; }} }}
      @keyframes abertura-ocre {{ to {{ fill: {OCRE}; filter: drop-shadow(0 0 18px rgba(227,174,78,.55)); }} }}
      @keyframes abertura-surgir {{ to {{ opacity: 1; transform: none; }} }}
      @media (prefers-reduced-motion: reduce) {{
        .abertura__simbolo path, .abertura__nome {{ animation: none; stroke-dashoffset: 0; opacity: 1; transform: none; }}
        .abertura__simbolo .a-base {{ fill: {CREME}; }}
        .abertura__simbolo .a-sol {{ fill: {OCRE}; }}
      }}
    </style>"""

tela = f"""<div id="abertura" aria-hidden="true">
      <svg class="abertura__simbolo" viewBox="{caixa(SIMBOLO)}">{simbolo}</svg>
      <svg class="abertura__nome" viewBox="{caixa(NOME)}">{nome}</svg>
    </div>"""

html = INDEX.read_text()
html = re.sub(r"\s*<!-- ABERTURA-ESTILO -->.*?<!-- /ABERTURA-ESTILO -->", "", html, flags=re.S)
html = re.sub(r"\s*<!-- ABERTURA -->.*?<!-- /ABERTURA -->", "", html, flags=re.S)
html = html.replace("  </head>", f"    <!-- ABERTURA-ESTILO -->\n    {estilo}\n    <!-- /ABERTURA-ESTILO -->\n  </head>")
html = html.replace("  <body>\n", f"  <body>\n    <!-- ABERTURA -->\n    <!-- gerado por marca/fonte/gerar_abertura.py -->\n    {tela}\n    <!-- /ABERTURA -->\n")
INDEX.write_text(html)
print(f"abertura escrita em {INDEX} ({len(html) // 1024} KB)")
