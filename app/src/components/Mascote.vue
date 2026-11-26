<!-- gerado por marca/fonte/gerar_mascote.py: não editar à mão -->
<template>
  <svg
    class="mascote"
    :viewBox="`0 0 ${TAMANHOS[pose][0]} ${TAMANHOS[pose][1]}`"
    :role="rotulo ? 'img' : undefined"
    :aria-label="rotulo"
    :aria-hidden="rotulo ? undefined : 'true'"
    v-html="desenho"
  />
</template>

<script lang="ts">
export type PoseMascote = 'trote' | 'parado' | 'aprovando' | 'duvida' | 'espiando' | 'empinando' | 'relinchando'

// o tamanho vem junto (a tela já reserva o espaço); o desenho de cada pose é baixado só quando aparece
const TAMANHOS: Record<PoseMascote, [number, number]> = {
  trote: [466, 446],
  parado: [290, 461],
  aprovando: [311, 459],
  duvida: [274, 454],
  espiando: [162, 437],
  empinando: [371, 469],
  relinchando: [466, 473],
}
const CARREGAR: Record<PoseMascote, () => Promise<{ default: string }>> = {
  trote: () => import('./mascote/trote'),
  parado: () => import('./mascote/parado'),
  aprovando: () => import('./mascote/aprovando'),
  duvida: () => import('./mascote/duvida'),
  espiando: () => import('./mascote/espiando'),
  empinando: () => import('./mascote/empinando'),
  relinchando: () => import('./mascote/relinchando'),
}
const baixados = new Map<PoseMascote, string>()

/** Baixa a pose antes de ela aparecer (ex.: a comemoração depois de salvar). */
export async function precarregarMascote(pose: PoseMascote) {
  if (!baixados.has(pose)) baixados.set(pose, (await CARREGAR[pose]()).default)
  return baixados.get(pose) as string
}
</script>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{ pose: PoseMascote; rotulo?: string }>()

const desenho = ref(baixados.get(props.pose) ?? '')
watch(
  () => props.pose,
  async (pose) => {
    desenho.value = baixados.get(pose) ?? ''
    const svg = await precarregarMascote(pose)
    if (props.pose === pose) desenho.value = svg
  },
  { immediate: true },
)
</script>

<style scoped>
.mascote {
  --m-contorno: transparent;
  --m-corpo: #D08A4C;
  --m-sombra: #B0682C;
  --m-crina: #1F2B4D;
  --m-creme: #FDE8CF;
  --m-escuro: #8C5018;
  display: block;
  width: 100%;
  height: auto;
}

/* no escuro a crina azul-noite sumiria: o contorno creme de adesivo separa o cavalo do fundo */
@media (prefers-color-scheme: dark) {
  .mascote {
    --m-contorno: #FAF6EE;
  }
}

.mascote :deep(.m-contorno) { fill: var(--m-contorno); }
.mascote :deep(.m-corpo) { fill: var(--m-corpo); }
.mascote :deep(.m-sombra) { fill: var(--m-sombra); }
.mascote :deep(.m-crina) { fill: var(--m-crina); }
.mascote :deep(.m-creme) { fill: var(--m-creme); }
.mascote :deep(.m-escuro) { fill: var(--m-escuro); }
</style>
