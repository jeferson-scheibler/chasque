"""Mascote do Chasque: vetoriza as 7 poses da folha de referência em camadas de cor.

A folha (marca/original/mascote-referencia.webp) foi gerada por imagem; aqui cada pose é
recortada, as cores são separadas pela paleta da marca, os contornos são suavizados
(tira o serrilhado e os calombos do traço gerado) e o potrace devolve curvas limpas.

Camadas, de baixo para cima:
  corpo     azul-noite, a silhueta inteira (passa um pouco por baixo das outras, sem fresta)
  couro     marrom da mochila e do toco
  lenco     ocre: lenço, cuia, sombra do chão, grama, "?" e o selo de aprovado
  metal     a bomba do chimarrão
  detalhe   creme: olhos, listras do poncho, faixa do chapéu, rédeas, check

Cada camada usa uma variável CSS, então o tema escuro é só troca de cor.

Uso (dentro da imagem chasque-ferramentas, que tem potrace, numpy e scipy):
  python marca/fonte/gerar_mascote.py               gera app/src/components/Mascote.vue
  python marca/fonte/gerar_mascote.py --previa DIR  também grava folhas de prévia (claro e escuro)
"""

import pathlib
import re
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image
from scipy import ndimage

RAIZ = pathlib.Path(__file__).resolve().parents[2]
REFERENCIA = RAIZ / "marca/original/mascote-referencia.webp"
DESTINO = RAIZ / "app/src/components/Mascote.vue"

# recorte aproximado de cada pose na folha 1536x1024 (x0, y0, x1, y1)
POSES = {
    "cavalo": (130, 20, 700, 505),
    "acenando": (770, 40, 1090, 490),
    "aprovando": (1165, 60, 1500, 490),
    "duvida": (55, 530, 380, 965),
    "caminho": (440, 530, 740, 960),
    "espiando": (820, 530, 1100, 960),
    "mate": (1165, 530, 1500, 965),
}

# centros de cor medidos na referência
CORES = {
    "fundo": (247, 244, 233),
    "corpo": (30, 43, 75),
    "corpo2": (52, 68, 102),  # sela translúcida: vira corpo
    "lenco": (226, 166, 74),
    "couro": (138, 90, 46),
    "metal": (178, 182, 190),
    "corda": (226, 206, 160),  # rédeas e cabresto
}

ESCALA = 3  # traça em 3x: curvas mais finas sem perder dedos e cascos


def classificar(rgb):
    nomes = list(CORES)
    centros = np.array([CORES[n] for n in nomes], dtype=np.float32)
    d = ((rgb[:, :, None, :].astype(np.float32) - centros[None, None]) ** 2).sum(-1)
    idx = d.argmin(-1)
    return {n: idx == i for i, n in enumerate(nomes)}


def disco(r):
    y, x = np.ogrid[-r : r + 1, -r : r + 1]
    return x * x + y * y <= r * r


def suavizar(mascara, sigma):
    """Amplia e borra antes de limiarizar: some o serrilhado e os calombos pequenos."""
    grande = np.asarray(
        Image.fromarray((mascara * 255).astype(np.uint8)).resize(
            (mascara.shape[1] * ESCALA, mascara.shape[0] * ESCALA), Image.BILINEAR
        ),
        dtype=np.float32,
    )
    return ndimage.gaussian_filter(grande, sigma * ESCALA) > 127


def tracar(mascara, minimo=40):
    """potrace -> atributo d em coordenadas da pose (px da referência)."""
    if not mascara.any():
        return ""
    with tempfile.TemporaryDirectory() as tmp:
        pbm = pathlib.Path(tmp) / "m.pbm"
        svg = pathlib.Path(tmp) / "m.svg"
        Image.fromarray(np.where(mascara, 0, 255).astype(np.uint8)).convert("1").save(pbm)
        subprocess.run(
            ["potrace", "-s", "--flat", "-u", "10", "-t", str(minimo * ESCALA * ESCALA),
             "-a", "1.15", "-O", "0.6", str(pbm), "-o", str(svg)],
            check=True,
        )
        texto = svg.read_text()
    altura = mascara.shape[0]
    d = " ".join(re.findall(r'<path d="([^"]+)"', texto))
    return reescalar(d, altura)


def reescalar(d, altura):
    """potrace devolve coordenadas em décimos de px com y invertido; traz para px da pose."""
    tokens = re.findall(r"[MmLlCcZz]|-?\d+\.?\d*", d)
    saida, cmd, nums, absoluto = [], None, [], True
    px = py = 0.0
    inicio = (0.0, 0.0)

    def emitir():
        nonlocal px, py, inicio
        if cmd is None:
            return
        c = cmd.lower()
        passo = {"m": 2, "l": 2, "c": 6}[c]
        for k in range(0, len(nums), passo):
            g = nums[k : k + passo]
            pts = []
            for j in range(0, passo, 2):
                x, y = g[j] / 10, g[j + 1] / 10
                if cmd.islower():
                    x, y = px + x, py - y
                else:
                    y = altura - y
                pts.append((x, y))
            px, py = pts[-1]
            letra = "C" if c == "c" else ("M" if c == "m" and k == 0 else "L")
            if letra == "M":
                inicio = (px, py)
            saida.append(letra + " ".join(f"{x / ESCALA:.1f} {y / ESCALA:.1f}" for x, y in pts))

    for t in tokens:
        if t in "MmLlCcZz":
            emitir()
            if t in "Zz":
                saida.append("Z")
                px, py = inicio
                cmd, nums = None, []
                continue
            cmd, nums = t, []
        else:
            nums.append(float(t))
    emitir()
    # potrace usa y para cima: o primeiro M absoluto já vem invertido acima; relativos sobem com -dy
    return re.sub(r"(\d)\.0(?=\D)", r"\1", "".join(saida))


def chao(lenco, altura):
    """Sombra do chão e grama: manchas de ocre encostadas na base do recorte."""
    rot, n = ndimage.label(lenco)
    saida = np.zeros_like(lenco)
    base = np.nonzero(lenco.any(1))[0].max() if lenco.any() else 0
    for i, fatia in enumerate(ndimage.find_objects(rot), 1):
        if fatia[0].stop >= base - 3 and (fatia[0].stop - fatia[0].start) < 70:
            saida |= rot == i
    return saida


def camadas(nome, caixa, img):
    x0, y0, x1, y1 = caixa
    cores = classificar(img[y0:y1, x0:x1])
    corpo = cores["corpo"] | cores["corpo2"]
    lenco, couro, metal = cores["lenco"], cores["couro"], cores["metal"]
    if nome != "mate":
        # fora do chimarrão não há metal: o cinza claro é corda (rédeas) ou borda de detalhe
        metal = np.zeros_like(metal)

    if nome == "espiando":
        # no lugar da vara, um corte reto: a borda de verdade é a lateral do cartão no app
        x = int(corpo.sum(0)[:80].argmax()) + 5
        for m in (corpo, lenco, couro):
            m[:, :x] = False

    solo = chao(lenco | couro, y1 - y0)
    solo &= lenco  # grama e sombra são ocre; o toco (couro) fica
    objetos = corpo | lenco | couro | metal
    # silhueta fechada: preenche olhos, listras e frestas finas entre braço e corpo
    silhueta = ndimage.binary_fill_holes(ndimage.binary_closing(objetos & ~solo, disco(5)))
    silhueta = ndimage.binary_opening(silhueta, disco(2))
    # creme dentro da silhueta: olhos, listras, faixa do chapéu, rédeas (o creme da referência
    # é o mesmo do fundo, então a separação é por geometria, não por cor)
    detalhe = silhueta & ~objetos & ~ndimage.binary_dilation(solo, disco(2))
    rot, n = ndimage.label(detalhe)
    linhas = np.nonzero(silhueta.any(1))[0]
    corte = linhas.min() + 0.68 * (linhas.max() - linhas.min())
    manter = []
    for i, fatia in enumerate(ndimage.find_objects(rot), 1):
        area = int((rot[fatia] == i).sum())
        # frestas entre pernas e braços ficam na parte de baixo: no tema escuro virariam riscos claros
        if nome == "cavalo":
            # creme entre os fios da cola é fundo, não detalhe
            ok = fatia[1].start < 0.72 * silhueta.shape[1]
        else:
            ok = fatia[0].start < corte
        # sobra creme minúscula fora do corpo (a curva do "?") não é detalhe
        perto = (ndimage.binary_dilation(rot[fatia] == i, disco(3)) & corpo[fatia]).any()
        if area >= 30 and ok and (perto or area >= 80):
            manter.append(i)
    detalhe = np.isin(rot, manter)

    base = (corpo | detalhe | (ndimage.binary_dilation(corpo, disco(3)) & silhueta)) & ~solo
    # viewBox justo: recorta tudo no retângulo do desenho, com folga para o borrão do traço
    tudo = base | solo | lenco | couro | metal | detalhe
    ys, xs = np.nonzero(tudo)
    folga = 6
    ya, yb = max(0, ys.min() - folga), min(tudo.shape[0], ys.max() + folga + 1)
    xa = xs.min() if nome == "espiando" else max(0, xs.min() - folga)  # o corte reto encosta na borda
    xb = min(tudo.shape[1], xs.max() + folga + 1)
    base, solo, lenco, couro, metal, detalhe = (m[ya:yb, xa:xb] for m in (base, solo, lenco, couro, metal, detalhe))
    return {
        "corpo": tracar(suavizar(base, 3.0), 60),
        "couro": tracar(suavizar(couro, 1.6)),
        "lenco": tracar(suavizar(lenco, 1.4), 25),
        "metal": tracar(suavizar(metal, 0.9), 8),
        "detalhe": tracar(suavizar(detalhe, 1.1), 20),
    }, (xb - xa, yb - ya)


ORDEM = ("corpo", "couro", "lenco", "metal", "detalhe")


def svg_pose(cam, tamanho, cores=None):
    w, h = tamanho
    corpo = "".join(
        f'<path class="m-{k}" d="{cam[k]}"/>' if cores is None else f'<path fill="{cores[k]}" d="{cam[k]}"/>'
        for k in ORDEM
        if cam[k]
    )
    return w, h, corpo


TEMAS = {
    "claro": {"fundo": "#FAF6EE", "corpo": "#1F2B4D", "couro": "#8A5A3C", "lenco": "#D99A2B",
              "metal": "#B9BEC8", "detalhe": "#FAF6EE"},
    "escuro": {"fundo": "#0F1524", "corpo": "#3A4A75", "couro": "#9C6A48", "lenco": "#E3AE4E",
               "metal": "#C9CED8", "detalhe": "#F3ECDD"},
}


def previa(poses, pasta):
    pasta.mkdir(parents=True, exist_ok=True)
    for tema, cores in TEMAS.items():
        x, blocos, alt = 30, [], max(t[1] for _, t in poses.values()) + 60
        for nome, (cam, tam) in poses.items():
            w, h, corpo = svg_pose(cam, tam, cores)
            blocos.append(f'<g transform="translate({x} {alt - h - 30})">{corpo}</g>')
            x += w + 30
        (pasta / f"mascote-{tema}.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {x} {alt}" width="{x}" height="{alt}">'
            f'<rect width="{x}" height="{alt}" fill="{cores["fundo"]}"/>{"".join(blocos)}</svg>'
        )


def componente(poses):
    entradas = []
    for nome, (cam, tam) in poses.items():
        w, h, corpo = svg_pose(cam, tam)
        entradas.append(f"  {nome}: {{ w: {w}, h: {h}, svg: `{corpo}` }},")
    tipos = " | ".join(f"'{n}'" for n in poses)
    return f"""<!-- gerado por marca/fonte/gerar_mascote.py: não editar à mão -->
<template>
  <svg
    class="mascote"
    :viewBox="`0 0 ${{pose.w}} ${{pose.h}}`"
    :role="rotulo ? 'img' : undefined"
    :aria-label="rotulo"
    :aria-hidden="rotulo ? undefined : 'true'"
    v-html="pose.svg"
  />
</template>

<script setup lang="ts">
import {{ computed }} from 'vue'

export type PoseMascote = {tipos}

const props = defineProps<{{ pose: PoseMascote; rotulo?: string }}>()

const POSES: Record<PoseMascote, {{ w: number; h: number; svg: string }}> = {{
{chr(10).join(entradas)}
}}

const pose = computed(() => POSES[props.pose])
</script>

<style scoped>
.mascote {{
  --m-corpo: {TEMAS["claro"]["corpo"]};
  --m-couro: {TEMAS["claro"]["couro"]};
  --m-lenco: {TEMAS["claro"]["lenco"]};
  --m-metal: {TEMAS["claro"]["metal"]};
  --m-detalhe: {TEMAS["claro"]["detalhe"]};
  display: block;
  width: 100%;
  height: auto;
}}

@media (prefers-color-scheme: dark) {{
  .mascote {{
    --m-corpo: {TEMAS["escuro"]["corpo"]};
    --m-couro: {TEMAS["escuro"]["couro"]};
    --m-lenco: {TEMAS["escuro"]["lenco"]};
    --m-metal: {TEMAS["escuro"]["metal"]};
    --m-detalhe: {TEMAS["escuro"]["detalhe"]};
  }}
}}

.mascote :deep(.m-corpo) {{ fill: var(--m-corpo); }}
.mascote :deep(.m-couro) {{ fill: var(--m-couro); }}
.mascote :deep(.m-lenco) {{ fill: var(--m-lenco); }}
.mascote :deep(.m-metal) {{ fill: var(--m-metal); }}
.mascote :deep(.m-detalhe) {{ fill: var(--m-detalhe); }}
</style>
"""


def main():
    img = np.asarray(Image.open(REFERENCIA).convert("RGB"))
    poses = {n: camadas(n, c, img) for n, c in POSES.items()}
    if "--previa" in sys.argv:
        previa(poses, pathlib.Path(sys.argv[sys.argv.index("--previa") + 1]))
    DESTINO.write_text(componente(poses))
    print(f"{DESTINO} ({DESTINO.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
