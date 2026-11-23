"""Monta uma folha de revisão: símbolo grande, invertido e em 48 e 16 px. Uso: python folha.py entrada_dir saida.png"""
import subprocess, sys
from PIL import Image
d = sys.argv[1]
def png(svg, w, fundo):
    subprocess.run(["rsvg-convert", "-w", str(w), "-b", fundo, f"{d}/{svg}", "-o", "/tmp/x.png"], check=True)
    return Image.open("/tmp/x.png").convert("RGBA")
folha = Image.new("RGBA", (980, 300), "#FAF6EE")
folha.paste(png("simbolo.svg", 240, "#FAF6EE"), (20, 30))
inv = Image.new("RGBA", (260, 260), "#1F2B4D"); inv.paste(png("simbolo-claro.svg", 220, "#1F2B4D"), (20, 20))
folha.paste(inv, (290, 20))
x = 590
for w, arq in ((96, "simbolo.svg"), (48, "simbolo.svg"), (32, "simbolo.svg"), (16, "simbolo.svg")):
    folha.paste(png(arq, w, "#FAF6EE"), (x, 150 - w // 2)); x += w + 30
folha.save(sys.argv[2])
