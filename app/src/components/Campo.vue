<template>
  <!-- Campo de formulário do Chasque: rótulo em cima, caixa clara arredondada, erro embaixo. -->
  <label class="campo-f" :class="{ 'campo-f--erro': erro }">
    <span class="campo-f__rotulo">{{ rotulo }}</span>
    <span class="campo-f__caixa">
      <input
        v-bind="$attrs"
        :type="tipoAtual"
        :value="modelValue"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
      <button
        v-if="type === 'password'"
        type="button"
        class="campo-f__olho"
        :aria-label="visivel ? 'Esconder senha' : 'Mostrar senha'"
        @click="visivel = !visivel"
      >
        <ion-icon :icon="visivel ? eyeOffOutline : eyeOutline" aria-hidden="true" />
      </button>
    </span>
    <span v-if="ajuda && !erro" class="campo-f__ajuda">{{ ajuda }}</span>
    <span v-if="erro" class="campo-f__erro" role="alert">{{ erro }}</span>
  </label>
</template>

<script setup lang="ts">
import { IonIcon } from '@ionic/vue'
import { eyeOffOutline, eyeOutline } from 'ionicons/icons'
import { computed, ref } from 'vue'

defineOptions({ inheritAttrs: false })
const props = withDefaults(
  defineProps<{ modelValue: string; rotulo: string; type?: string; ajuda?: string; erro?: string }>(),
  { type: 'text', ajuda: '', erro: '' },
)
const emit = defineEmits<{ 'update:modelValue': [valor: string] }>()

const visivel = ref(false)
const tipoAtual = computed(() => (props.type === 'password' && visivel.value ? 'text' : props.type))
</script>

<style scoped>
.campo-f {
  display: block;
  margin-bottom: 16px;
}

.campo-f__rotulo {
  display: block;
  margin: 0 0 6px 2px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--chasque-tinta);
}

.campo-f__caixa {
  display: flex;
  align-items: center;
  border-radius: 14px;
  background: var(--chasque-papel);
  border: 1.5px solid var(--chasque-neblina);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.campo-f__caixa:focus-within {
  border-color: var(--chasque-faixa);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--chasque-faixa) 12%, transparent);
}

@media (prefers-color-scheme: dark) {
  .campo-f__caixa:focus-within {
    border-color: var(--ion-color-primary);
  }
}

.campo-f--erro .campo-f__caixa {
  border-color: var(--ion-color-danger);
}

input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  padding: 14px 14px;
  font: inherit;
  font-size: 1rem;
  color: var(--chasque-tinta);
}

input::placeholder {
  color: var(--ion-placeholder-color);
}

.campo-f__olho {
  border: 0;
  background: transparent;
  color: var(--chasque-tinta-suave);
  padding: 0 14px;
  height: 48px;
  font-size: 20px;
  display: grid;
  place-items: center;
}

.campo-f__ajuda,
.campo-f__erro {
  display: block;
  margin: 6px 2px 0;
  font-size: 0.8rem;
  color: var(--chasque-tinta-suave);
}

.campo-f__erro {
  color: var(--ion-color-danger);
}
</style>
