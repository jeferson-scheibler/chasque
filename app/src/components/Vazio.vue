<template>
  <section class="vazio" :class="{ 'vazio--espiando': pose === 'espiando' }">
    <div class="vazio__mascote"><mascote :pose="pose" /></div>
    <h2>{{ titulo }}</h2>
    <p>{{ texto }}</p>
    <slot />
  </section>
</template>

<script setup lang="ts">
import Mascote, { type PoseMascote } from './Mascote.vue'

defineProps<{ titulo: string; texto: string; pose: PoseMascote }>()
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

.vazio--espiando .vazio__mascote .mascote {
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
  .vazio__mascote {
    animation: none;
  }
}
</style>
