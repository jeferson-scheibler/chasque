"""Ícones do app a partir do símbolo. Rodar no container de ferramentas: python gerar_icones.py <marca> <saida>"""
import re
import subprocess
import sys

MARCA, SAIDA = sys.argv[1], sys.argv[2]
NOITE = "#1F2B4D"


def interno(arquivo):
    """O símbolo como <svg> aninhado num quadrado 120x120, centralizado (o símbolo é mais largo que alto)."""
    svg = open(f"{MARCA}/{arquivo}").read()
    caixa = re.search(r'viewBox="([^"]+)"', svg).group(1)
    corpo = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
    return f'<svg x="0" y="0" width="120" height="120" viewBox="{caixa}">{corpo}</svg>'


def icone(arquivo_simbolo, proporcao, raio=0):
    """Fundo Noite com o símbolo claro centralizado ocupando `proporcao` do lado."""
    lado = 120 / proporcao
    m = (lado - 120) / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-m:.2f} {-m:.2f} {lado:.2f} {lado:.2f}">
  <rect x="{-m:.2f}" y="{-m:.2f}" width="{lado:.2f}" height="{lado:.2f}" rx="{raio * lado:.2f}" fill="{NOITE}"/>
{interno(arquivo_simbolo)}
</svg>
"""


# Maskable: a área segura é um círculo de 80% do lado; o símbolo fica em 62%.
open(f"{SAIDA}/icone-maskable.svg", "w").write(icone("simbolo-claro.svg", 0.66))
open(f"{SAIDA}/icone.svg", "w").write(icone("simbolo-claro.svg", 0.76, raio=0.22))
open(f"{SAIDA}/favicon.svg", "w").write(icone("simbolo-claro.svg", 0.84, raio=0.22))

for arquivo, tamanho, nome in [
    ("icone.svg", 192, "icone-192.png"),
    ("icone.svg", 512, "icone-512.png"),
    ("icone-maskable.svg", 512, "icone-maskable-512.png"),
    ("icone-maskable.svg", 180, "apple-touch-icon.png"),
    ("favicon.svg", 32, "favicon-32.png"),
]:
    subprocess.run(["rsvg-convert", "-w", str(tamanho), f"{SAIDA}/{arquivo}", "-o", f"{SAIDA}/{nome}"], check=True)
