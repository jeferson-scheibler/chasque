<template>
  <section class="vazio">
    <div class="vazio__simbolo"><simbolo-contorno /></div>
    <h2>{{ titulo }}</h2>
    <p>{{ texto }}</p>
    <slot />
  </section>
</template>

<script setup lang="ts">
import SimboloContorno from './SimboloContorno.vue'

defineProps<{ titulo: string; texto: string }>()
</script>

<style scoped>
.vazio {
  max-width: 340px;
  margin: 0 auto;
  padding: 40px 24px 32px;
  text-align: center;
}

.vazio__simbolo {
  width: 150px;
  margin: 8px auto 28px;
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
</style>
