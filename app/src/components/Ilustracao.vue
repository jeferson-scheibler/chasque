<template>
  <svg class="ilustracao" :viewBox="desenho.viewBox" :role="rotulo ? 'img' : undefined" :aria-label="rotulo" :aria-hidden="rotulo ? undefined : 'true'">
    <path v-for="(d, i) in desenho.tinta" :key="`t${i}`" class="ilustracao__tinta" :d="d" fill-rule="evenodd" />
    <path v-for="(d, i) in desenho.acento" :key="`a${i}`" class="ilustracao__acento" :d="d" fill-rule="evenodd" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ILUSTRACOES, type NomeIlustracao } from './ilustracoes'

const props = defineProps<{ nome: NomeIlustracao; rotulo?: string }>()
const desenho = computed(() => ILUSTRACOES[props.nome])
</script>

<style scoped>
/* tinta azul-noite no claro e creme no escuro; o acento é o ocre. Sobre a faixa azul, troque --ilustracao-tinta. */
.ilustracao {
  display: block;
  width: 100%;
  height: auto;
}

.ilustracao__tinta {
  fill: var(--ilustracao-tinta, var(--chasque-ilustracao));
}

.ilustracao__acento {
  fill: var(--ilustracao-acento, var(--chasque-ocre));
}
</style>
