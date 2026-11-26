"""Mascote do Chasque: um cavalo crioulo em 7 poses, vetorizado a partir de uma folha de adesivos.

A folha (marca/original/Folha de Adesivos de Pôneis Fofos.png) tem fundo transparente, então a silhueta sai do
canal alfa. Dentro dela, cada pixel vai para a cor mais próxima da paleta e cada cor vira uma camada traçada
pelo potrace, com variável CSS própria (o tema muda as variáveis, não o desenho):

  contorno  borda de adesivo: só aparece no tema escuro, onde o azul-noite da crina sumiria
  corpo     baio, a silhueta inteira (as demais camadas ficam por cima, sem fresta)
  sombra    baio mais escuro: pernas do lado de lá, parte de dentro da orelha
  crina     azul-noite: crina, cola, cascos, pupila
  creme     focinho, pelego, brilho do olho, cabresto
  escuro    lenço, cincha, bolsa, grama, riscos de som, interrogação e check

Para pesar pouco: coordenadas inteiras e relativas (o desenho tem ~450 px de altura e aparece com menos de 250,
então meio pixel não se vê), e cada pose num arquivo próprio, que a tela só baixa quando mostra aquela pose.

Uso (na imagem chasque-ferramentas, que tem potrace, numpy e scipy):
  python marca/fonte/gerar_mascote.py               gera app/src/components/Mascote.vue e mascote/<pose>.ts
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

ESCALA = 3  # traça em 3x: curvas mais finas sem perder dedos e cascos


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
    return compactar("".join(saida))


def compactar(d):
    """Caminho absoluto (M, L, C, Z; um segmento por letra) -> relativo, com inteiros e sem separador sobrando:
    "m12 30c4-2 8 0 9 5z". Arredonda as posições absolutas e só depois tira a diferença: o erro não se acumula."""
    saida, atual, inicio, ultimo = [], (0, 0), (0, 0), None
    for cmd, numeros in re.findall(r"([MLCZ])([^MLCZ]*)", d):
        if cmd == "Z":
            saida.append("z")
            atual, ultimo = inicio, None
            continue
        pts = [round(float(n)) for n in re.findall(r"-?\d+(?:\.\d+)?", numeros)]
        # num C os três pares são relativos ao ponto de antes do segmento
        rel = [v - atual[i % 2] for i, v in enumerate(pts)]
        texto = "".join(("" if j == 0 or v < 0 else " ") + str(v) for j, v in enumerate(rel))
        letra = cmd.lower()
        if letra == ultimo:  # mesma letra de antes: dá para omitir, separando o número se precisar
            saida.append(texto if texto.startswith("-") else " " + texto)
        else:
            saida.append(letra + texto)
        atual = (pts[-2], pts[-1])
        if letra == "m":
            inicio, ultimo = atual, "l"  # depois de um m, pares soltos já valem como l
        else:
            ultimo = letra
    return "".join(saida)


RAIZ = pathlib.Path(__file__).resolve().parents[2]
REFERENCIA = RAIZ / "marca/original/Folha de Adesivos de Pôneis Fofos.png"
DESTINO = RAIZ / "app/src/components/Mascote.vue"
PASTA_POSES = RAIZ / "app/src/components/mascote"

NOMES = ["trote", "parado", "aprovando", "duvida", "espiando", "empinando", "relinchando"]

CENTROS = {
    "corpo": (212, 139, 76),
    "sombra": (176, 104, 44),
    "crina": (30, 42, 66),
    "creme": (253, 232, 207),
    "escuro": (140, 80, 24),
}
ORDEM = ("contorno", "corpo", "sombra", "crina", "creme", "escuro")

# as cores do cavalo são as mesmas nos dois temas; no escuro só entra o contorno de adesivo
CORES = {"corpo": "#D08A4C", "sombra": "#B0682C", "crina": "#1F2B4D", "creme": "#FDE8CF", "escuro": "#8C5018"}
CONTORNO = {"claro": "transparent", "escuro": "#FAF6EE"}
FUNDO = {"claro": "#FAF6EE", "escuro": "#0F1524"}

MARGEM = 14  # folga em volta da pose para caber o contorno de adesivo
ENGORDAR = 10  # espessura do contorno, em px da referência

# recorte de cada pose na folha 1536x1024 (y0, y1, x0, x1): a grade é irregular, então é medida à mão
CAIXAS = [
    (0, 490, 0, 500), (0, 490, 500, 830), (0, 490, 830, 1200), (0, 490, 1200, 1536),
    (500, 1024, 0, 420), (500, 1024, 420, 860), (500, 1024, 860, 1536),
]


def camadas(nome, img, alfa, caixa):
    y0, y1, x0, x1 = caixa
    rgb = img[y0:y1, x0:x1]
    a = alfa[y0:y1, x0:x1]
    nomes = list(CENTROS)
    c = np.array([CENTROS[n] for n in nomes], dtype=np.float32)
    d = ((rgb[:, :, None, :].astype(np.float32) - c[None, None]) ** 2).sum(-1)
    idx = d.argmin(-1)
    mascaras = {n: (idx == i) & a for i, n in enumerate(nomes)}
    # a silhueta fechada vira o corpo: nenhum buraco entre camadas
    mascaras["corpo"] = ndimage.binary_closing(a, disco(3))
    ys, xs = np.nonzero(a)
    ya, yb, xa, xb = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    # o "espiando" tem um lado cortado reto: sem folga à esquerda, para encostar na borda da tela
    esq = 0 if nome == "espiando" else MARGEM
    pad = ((MARGEM, MARGEM), (esq, MARGEM))
    recorte = {n: np.pad(m[ya:yb, xa:xb], pad) for n, m in mascaras.items()}
    gordo = ndimage.binary_dilation(recorte["corpo"], disco(ENGORDAR))
    if nome == "espiando":
        gordo[:, :esq + 1] &= recorte["corpo"][:, :esq + 1]  # nada de contorno do lado da borda
        gordo[:, 0] = False
    recorte["contorno"] = gordo
    ajustes = {"contorno": (2.4, 80), "corpo": (1.4, 60), "sombra": (1.2, 40), "crina": (1.1, 30),
               "creme": (1.0, 14), "escuro": (1.0, 14)}
    saida = {n: tracar(suavizar(recorte[n], ajustes[n][0]), ajustes[n][1]) for n in ORDEM}
    h, w = recorte["corpo"].shape
    return saida, (w, h)


def svg_pose(cam, tam, tema=None):
    """tema None: classes CSS (componente); 'claro' ou 'escuro': cores fixas (prévia)."""
    def cor(k):
        return CONTORNO[tema] if k == "contorno" else CORES[k]
    return tam[0], tam[1], "".join(
        (f'<path class="m-{k}" d="{cam[k]}"/>' if tema is None else f'<path fill="{cor(k)}" d="{cam[k]}"/>')
        for k in ORDEM if cam[k]
    )


def previa(poses, pasta):
    pasta.mkdir(parents=True, exist_ok=True)
    for tema in ("claro", "escuro"):
        x, blocos = 30, []
        alt = max(t[1] for _, t in poses.values()) + 60
        for cam, tam in poses.values():
            w, h, corpo = svg_pose(cam, tam, tema)
            blocos.append(f'<g transform="translate({x} {alt - h - 30})">{corpo}</g>')
            x += w + 30
        (pasta / f"mascote-{tema}.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {x} {alt}" width="{x}" height="{alt}">'
            f'<rect width="{x}" height="{alt}" fill="{FUNDO[tema]}"/>{"".join(blocos)}</svg>'
        )


def componente(poses):
    tamanhos = "\n".join(f"  {nome}: [{tam[0]}, {tam[1]}]," for nome, (_, tam) in poses.items())
    carregar = "\n".join(f"  {nome}: () => import('./mascote/{nome}')," for nome in poses)
    tipos = " | ".join(f"'{n}'" for n in poses)
    regras = "\n".join(f".mascote :deep(.m-{k}) {{ fill: var(--m-{k}); }}" for k in ORDEM)
    return f"""<!-- gerado por marca/fonte/gerar_mascote.py: não editar à mão -->
<template>
  <svg
    class="mascote"
    :viewBox="`0 0 ${{TAMANHOS[pose][0]}} ${{TAMANHOS[pose][1]}}`"
    :role="rotulo ? 'img' : undefined"
    :aria-label="rotulo"
    :aria-hidden="rotulo ? undefined : 'true'"
    v-html="desenho"
  />
</template>

<script lang="ts">
export type PoseMascote = {tipos}

// o tamanho vem junto (a tela já reserva o espaço); o desenho de cada pose é baixado só quando aparece
const TAMANHOS: Record<PoseMascote, [number, number]> = {{
{tamanhos}
}}
const CARREGAR: Record<PoseMascote, () => Promise<{{ default: string }}>> = {{
{carregar}
}}
const baixados = new Map<PoseMascote, string>()

/** Baixa a pose antes de ela aparecer (ex.: a comemoração depois de salvar). */
export async function precarregarMascote(pose: PoseMascote) {{
  if (!baixados.has(pose)) baixados.set(pose, (await CARREGAR[pose]()).default)
  return baixados.get(pose) as string
}}
</script>

<script setup lang="ts">
import {{ ref, watch }} from 'vue'

const props = defineProps<{{ pose: PoseMascote; rotulo?: string }}>()

const desenho = ref(baixados.get(props.pose) ?? '')
watch(
  () => props.pose,
  async (pose) => {{
    desenho.value = baixados.get(pose) ?? ''
    const svg = await precarregarMascote(pose)
    if (props.pose === pose) desenho.value = svg
  }},
  {{ immediate: true }},
)
</script>

<style scoped>
.mascote {{
  --m-contorno: {CONTORNO["claro"]};
  --m-corpo: {CORES["corpo"]};
  --m-sombra: {CORES["sombra"]};
  --m-crina: {CORES["crina"]};
  --m-creme: {CORES["creme"]};
  --m-escuro: {CORES["escuro"]};
  display: block;
  width: 100%;
  height: auto;
}}

/* no escuro a crina azul-noite sumiria: o contorno creme de adesivo separa o cavalo do fundo */
@media (prefers-color-scheme: dark) {{
  .mascote {{
    --m-contorno: {CONTORNO["escuro"]};
  }}
}}

{regras}
</style>
"""


def arquivo_da_pose(cam, tam):
    _, _, corpo = svg_pose(cam, tam)
    return f"// gerado por marca/fonte/gerar_mascote.py: não editar à mão\nexport default `{corpo}`\n"


def main():
    arr = np.asarray(Image.open(REFERENCIA).convert("RGBA"))
    alfa = arr[:, :, 3] > 128
    img = arr[:, :, :3]
    poses = {n: camadas(n, img, alfa, c) for n, c in zip(NOMES, CAIXAS)}
    if "--previa" in sys.argv:
        previa(poses, pathlib.Path(sys.argv[sys.argv.index("--previa") + 1]))
    DESTINO.write_text(componente(poses))
    PASTA_POSES.mkdir(exist_ok=True)
    for nome, (cam, tam) in poses.items():
        destino = PASTA_POSES / f"{nome}.ts"
        destino.write_text(arquivo_da_pose(cam, tam))
        print(f"{destino.name}: {destino.stat().st_size / 1024:.1f} KB")
    print(f"{DESTINO} ({DESTINO.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
