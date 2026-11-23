<template>
  <!-- Fichas para escolher: uma (ocasião) ou várias (motivos). Marcadas ficam na cor da faixa, com um visto. -->
  <div class="escolhas" :role="multipla ? 'group' : 'radiogroup'" :aria-label="rotulo">
    <button
      v-for="opcao in opcoes"
      :key="opcao.valor"
      type="button"
      class="ficha"
      :class="{ marcada: marcada(opcao.valor) }"
      :role="multipla ? 'checkbox' : 'radio'"
      :aria-checked="marcada(opcao.valor)"
      @click="alternar(opcao.valor)"
    >
      <ion-icon v-if="marcada(opcao.valor)" :icon="checkmark" aria-hidden="true" class="ficha__visto" />
      <ion-icon v-else-if="opcao.icone" :icon="opcao.icone" aria-hidden="true" />
      {{ opcao.rotulo }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { IonIcon } from '@ionic/vue'
import { checkmark } from 'ionicons/icons'

export interface Opcao {
  valor: string
  rotulo: string
  icone?: string
}

const props = defineProps<{ opcoes: Opcao[]; modelValue: string[] | string | null; multipla?: boolean; rotulo: string }>()
const emit = defineEmits<{ 'update:modelValue': [valor: string[] | string] }>()

function marcada(valor: string) {
  return Array.isArray(props.modelValue) ? props.modelValue.includes(valor) : props.modelValue === valor
}

function alternar(valor: string) {
  if (!props.multipla) {
    emit('update:modelValue', valor)
    return
  }
  const atual = Array.isArray(props.modelValue) ? props.modelValue : []
  emit('update:modelValue', atual.includes(valor) ? atual.filter((v) => v !== valor) : [...atual, valor])
}
</script>

<style scoped>
.escolhas {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ficha {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 40px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1.5px solid var(--chasque-neblina);
  background: var(--chasque-papel);
  color: var(--chasque-tinta);
  font: inherit;
  font-size: 0.92rem;
  font-weight: 500;
  transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease, transform 0.12s ease;
}

.ficha ion-icon {
  font-size: 17px;
  color: var(--chasque-tinta-suave);
}

.ficha:active {
  transform: scale(0.96);
}

.ficha.marcada {
  background: var(--chasque-faixa);
  border-color: var(--chasque-faixa);
  color: var(--chasque-faixa-texto);
}

.ficha.marcada .ficha__visto {
  color: var(--chasque-ocre);
}

@media (prefers-color-scheme: dark) {
  .ficha.marcada {
    background: var(--chasque-faixa-texto);
    border-color: var(--chasque-faixa-texto);
    color: var(--chasque-faixa);
  }

  .ficha.marcada .ficha__visto {
    color: var(--chasque-faixa);
  }
}
</style>
