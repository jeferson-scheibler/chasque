<template>
  <!--
    Nota de 1 a 5 em sóis (o sol do logo). Interativo: os sóis acendem em sequência até o tocado.
    Só leitura (pequeno): mostra a nota numa linha discreta.
  -->
  <div v-if="somenteLeitura" class="sois sois--leitura" role="img" :aria-label="`${modelValue} de 5: ${NOTAS[modelValue]}`">
    <ion-icon
      v-for="n in 5"
      :key="n"
      :icon="n <= modelValue ? sunny : sunnyOutline"
      :class="{ aceso: n <= modelValue }"
      aria-hidden="true"
    />
  </div>
  <div v-else class="sois-escolha">
    <div class="sois" role="radiogroup" aria-label="Como foi a visita">
      <button
        v-for="n in 5"
        :key="n"
        type="button"
        role="radio"
        :aria-checked="modelValue === n"
        :aria-label="`${n}: ${NOTAS[n]}`"
        :class="{ aceso: n <= modelValue }"
        :style="{ transitionDelay: `${(n - 1) * 45}ms` }"
        @click="emit('update:modelValue', n)"
      >
        <ion-icon :icon="n <= modelValue ? sunny : sunnyOutline" aria-hidden="true" />
      </button>
    </div>
    <p class="sois__rotulo" aria-live="polite">{{ modelValue ? NOTAS[modelValue] : 'Toque nos sóis' }}</p>
  </div>
</template>

<script setup lang="ts">
import { IonIcon } from '@ionic/vue'
import { sunny, sunnyOutline } from 'ionicons/icons'
import { NOTAS } from '@/types'

defineProps<{ modelValue: number; somenteLeitura?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [nota: number] }>()
</script>

<style scoped>
.sois {
  display: flex;
  gap: 6px;
}

.sois-escolha .sois {
  justify-content: space-between;
  max-width: 330px;
}

.sois-escolha button {
  width: 56px;
  height: 56px;
  border: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--chasque-neblina);
  color: var(--chasque-tinta-suave);
  font-size: 28px;
  transition: background-color 0.22s ease, color 0.22s ease, transform 0.22s cubic-bezier(0.3, 1.5, 0.5, 1),
    box-shadow 0.3s ease;
}

.sois-escolha button.aceso {
  background: var(--chasque-ocre);
  color: var(--chasque-sobre-ocre);
  transform: scale(1.06);
  box-shadow: 0 0 22px -2px var(--chasque-ocre-brilho);
}

.sois-escolha button:active {
  transform: scale(0.92);
}

.sois__rotulo {
  margin: 12px 0 0;
  font-family: var(--chasque-fonte-titulo);
  font-weight: 600;
  font-size: 1.05rem;
  color: var(--chasque-tinta);
  min-height: 1.4em;
}

.sois--leitura {
  gap: 2px;
  font-size: 14px;
  color: var(--chasque-neblina);
}

.sois--leitura .aceso {
  color: var(--chasque-ocre);
}
</style>
