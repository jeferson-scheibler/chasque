"""Folha de apresentação da marca. Rodar no container de ferramentas: python apresentacao.py <marca> <icones>"""
import subprocess
import sys

from PIL import Image

M, ICONES = sys.argv[1], sys.argv[2]
CREME, NOITE = "#FAF6EE", "#1F2B4D"


def png(caminho, altura=None, largura=None):
    args = ["rsvg-convert", caminho, "-o", "/tmp/p.png"]
    args += ["-h", str(altura)] if altura else ["-w", str(largura)]
    subprocess.run(args, check=True)
    return Image.open("/tmp/p.png").convert("RGBA")


folha = Image.new("RGBA", (1400, 900), CREME)
s = png(f"{M}/simbolo.svg", largura=340)
folha.alpha_composite(s, (70, (440 - s.height) // 2))
escuro = Image.new("RGBA", (440, 440), NOITE)
c = png(f"{M}/simbolo-claro.svg", largura=320)
escuro.alpha_composite(c, (60, (440 - c.height) // 2))
folha.alpha_composite(escuro, (480, 0))
icone = png(f"{ICONES}/icone.svg", largura=240)
folha.alpha_composite(icone, (1020, 100))
folha.alpha_composite(png(f"{M}/chasque-horizontal.svg", altura=150), (80, 520))
x = 980
for tam, arq in ((64, "simbolo.svg"), (32, "simbolo.svg"), (16, "simbolo.svg")):
    folha.alpha_composite(png(f"{M}/{arq}", largura=tam), (x, 595 - tam // 2))
    x += tam + 40
faixa = Image.new("RGBA", (1400, 160), NOITE)
faixa.alpha_composite(png(f"{M}/chasque-horizontal-claro.svg", altura=90), (80, 35))
folha.alpha_composite(faixa, (0, 740))
folha.convert("RGB").save(f"{M}/apresentacao.png")
