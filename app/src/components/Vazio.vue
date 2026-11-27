<template>
  <section class="vazio" :class="{ 'vazio--espiando': pose === 'espiando' }">
    <div v-if="ilustracao" class="vazio__ilustracao"><ilustracao :nome="ilustracao" /></div>
    <div v-else-if="pose" class="vazio__mascote"><mascote :pose="pose" /></div>
    <h2>{{ titulo }}</h2>
    <p>{{ texto }}</p>
    <slot />
  </section>
</template>

<script setup lang="ts">
import Ilustracao from './Ilustracao.vue'
import Mascote, { type PoseMascote } from './Mascote.vue'
import type { NomeIlustracao } from './ilustracoes'

/** Com `ilustracao`, mostra o desenho no lugar do mascote. */
defineProps<{ titulo: string; texto: string; pose?: PoseMascote; ilustracao?: NomeIlustracao }>()
</script>

<style scoped>
.vazio {
  max-width: 340px;
  margin: 0 auto;
  padding: 32px 24px 32px;
  text-align: center;
}

.vazio__mascote {
  margin: 0 auto 22px;
  animation: chegar 0.6s ease-out both;
}

.vazio__ilustracao {
  margin: 0 auto 22px;
  animation: chegar 0.6s ease-out both;
}

/* pela altura, como o mascote: desenho alto (a cuia) ou largo (o gaúcho) ocupam o mesmo espaço */
.vazio__ilustracao .ilustracao {
  height: 140px;
  width: auto;
  max-width: 100%;
  margin: 0 auto;
}

.vazio__mascote .mascote {
  height: 150px;
  width: auto;
  margin: 0 auto;
}

/* o espiando tem um lado cortado reto: encosta na borda esquerda da tela e olha para dentro */
.vazio--espiando {
  text-align: left;
}

.vazio--espiando .vazio__mascote {
  margin-left: calc(50% - 50vw);
  animation-name: espiar;
}

.vazio--espiando .vazio__ilustracao {
  margin: 0 auto 22px;
  animation: chegar 0.6s ease-out both;
}

/* pela altura, como o mascote: desenho alto (a cuia) ou largo (o gaúcho) ocupam o mesmo espaço */
.vazio__ilustracao .ilustracao {
  height: 140px;
  width: auto;
  max-width: 100%;
  margin: 0 auto;
}

.vazio__mascote .mascote {
  height: 200px;
  margin: 0;
}

.vazio h2 {
  margin: 0 0 8px;
  font-size: 1.35rem;
  font-weight: 650;
  line-height: 1.2;
  color: var(--chasque-tinta);
}

.vazio p {
  margin: 0 0 24px;
  color: var(--chasque-tinta-suave);
  line-height: 1.5;
}

@keyframes chegar {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
}

@keyframes espiar {
  from {
    transform: translateX(-60%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .vazio__mascote,
  .vazio__ilustracao {
    animation: none;
  }
}
</style>
