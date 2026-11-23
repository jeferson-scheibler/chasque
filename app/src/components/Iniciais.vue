<template>
  <!-- Círculo com as iniciais da pessoa. A cor vem do id, para cada pessoa ter sempre a mesma. -->
  <span class="iniciais" :class="`iniciais--${tamanho}`" :style="{ background: cor.fundo, color: cor.texto }" aria-hidden="true">
    {{ pessoa.iniciais || '?' }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Pessoa } from '@/types'

const props = withDefaults(defineProps<{ pessoa: Pessoa; tamanho?: 'p' | 'g' }>(), { tamanho: 'p' })

// Tons da marca: ocre, campo, noite claro, terracota suave.
const TONS = [
  { fundo: '#d99a2b', texto: '#1f2b4d' },
  { fundo: '#4f7a4a', texto: '#faf6ee' },
  { fundo: '#a9b7e0', texto: '#1f2b4d' },
  { fundo: '#c9876a', texto: '#1f2b4d' },
]
const cor = computed(() => TONS[props.pessoa.id % TONS.length])
</script>

<style scoped>
.iniciais {
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-family: var(--chasque-fonte-titulo);
  font-weight: 700;
}

.iniciais--p {
  width: 46px;
  height: 46px;
  font-size: 1rem;
}

.iniciais--g {
  width: 84px;
  height: 84px;
  font-size: 1.8rem;
}
</style>
