"""Gera as versões da marca a partir dos SVGs originais (exportados do Illustrator) em marca/original/.

- tira metadados e classes, e unifica as cores nas da marca (os azuis viram Noite, o laranja vira Ocre);
- recorta o viewBox justo no desenho;
- separa o nome (caminhos que não estão no símbolo).

Rodar no container de ferramentas (usa fontTools para medir os caminhos):
    python limpar_svg.py <pasta marca>
"""
import re
import sys
import xml.etree.ElementTree as ET

from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path

M = sys.argv[1]
NS = "{http://www.w3.org/2000/svg}"
NOITE, OCRE = "#1F2B4D", "#D99A2B"
CREME, OCRE_CLARO = "#FAF6EE", "#E3AE4E"


def caminhos(arquivo):
    """Lista de (d, papel) onde papel é 'sol' para o laranja e 'base' para os azuis."""
    raiz = ET.parse(arquivo).getroot()
    estilo = "".join(e.text or "" for e in raiz.iter(f"{NS}style"))
    cores = dict(re.findall(r"\.(cls-\d+)\s*\{\s*fill:\s*(#[0-9a-fA-F]{6})", estilo))
    saida = []
    for p in raiz.iter(f"{NS}path"):
        cor = cores.get(p.get("class"), p.get("fill", "#000000")).lower()
        r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
        saida.append((p.get("d"), "sol" if r > b + 60 else "base"))
    return saida


def caixa(lista):
    pen = BoundsPen(None)
    for d, _ in lista:
        parse_path(d, pen)
    return pen.bounds  # xmin, ymin, xmax, ymax


def escrever(nome, lista, cor_base, cor_sol, margem=0.0):
    x0, y0, x1, y1 = caixa(lista)
    m = margem * (y1 - y0)
    vb = " ".join(f"{v:.1f}".replace("-0.0", "0.0") for v in (x0 - m, y0 - m, x1 - x0 + 2 * m, y1 - y0 + 2 * m))
    corpo = "\n".join(f'  <path fill="{cor_sol if papel == "sol" else cor_base}" d="{d}"/>' for d, papel in lista)
    with open(f"{M}/{nome}", "w") as arq:
        arq.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">\n{corpo}\n</svg>\n')


simbolo = caminhos(f"{M}/original/logo-chasque-simbolo.svg")
completo = caminhos(f"{M}/original/logo-chasque.svg")
d_simbolo = {d for d, _ in simbolo}
nome = [c for c in completo if c[0] not in d_simbolo]

escrever("simbolo.svg", simbolo, NOITE, OCRE)
escrever("simbolo-claro.svg", simbolo, CREME, OCRE_CLARO)
escrever("chasque-horizontal.svg", completo, NOITE, OCRE)
escrever("chasque-horizontal-claro.svg", completo, CREME, OCRE_CLARO)
escrever("chasque-nome.svg", nome, NOITE, OCRE)
escrever("chasque-nome-claro.svg", nome, CREME, OCRE_CLARO)
print(f"símbolo: {len(simbolo)} caminhos, nome: {len(nome)} caminhos")
