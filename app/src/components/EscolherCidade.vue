<template>
  <!-- Cidade com busca: são 497 municípios no RS, uma lista para rolar não funciona no celular. -->
  <div class="cidade" @focusout="aoSair">
    <label :for="id" class="cidade__rotulo">Cidade</label>
    <div class="cidade__caixa" :class="{ 'cidade__caixa--escolhida': escolhida }">
      <ion-icon :icon="escolhida ? checkmarkCircle : searchOutline" aria-hidden="true" />
      <input
        :id="id"
        v-model="termo"
        type="text"
        autocomplete="off"
        autocapitalize="words"
        placeholder="Digite o nome da cidade"
        role="combobox"
        :aria-expanded="aberta"
        :aria-controls="`${id}-lista`"
        @focus="aberta = true"
        @input="aoDigitar"
        @keydown.down.prevent="mover(1)"
        @keydown.up.prevent="mover(-1)"
        @keydown.enter.prevent="escolherAtual"
        @keydown.esc="aberta = false"
      />
    </div>
    <ul v-if="aberta && sugestoes.length" :id="`${id}-lista`" class="cidade__lista" role="listbox">
      <li
        v-for="(cidade, i) in sugestoes"
        :key="cidade.id"
        role="option"
        :aria-selected="i === destaque"
        :class="{ destaque: i === destaque }"
        @mousedown.prevent="escolher(cidade)"
      >
        {{ cidade.nome }}
      </li>
    </ul>
    <p v-else-if="aberta && termo.trim().length >= 2" class="cidade__nada">Nenhuma cidade do RS com esse nome.</p>
  </div>
</template>

<script setup lang="ts">
import { IonIcon } from '@ionic/vue'
import { checkmarkCircle, searchOutline } from 'ionicons/icons'
import { computed, ref } from 'vue'
import type { Cidade } from '@/types'

const props = defineProps<{ cidades: Cidade[]; modelValue: number | null }>()
const emit = defineEmits<{ 'update:modelValue': [id: number | null] }>()

const id = `cidade-${Math.random().toString(36).slice(2, 8)}`
const termo = ref(props.cidades.find((c) => c.id === props.modelValue)?.nome ?? '')
const aberta = ref(false)
const destaque = ref(0)

const escolhida = computed(() => props.cidades.find((c) => c.id === props.modelValue) ?? null)

function normalizar(texto: string) {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

const indice = computed(() => props.cidades.map((c) => ({ cidade: c, chave: normalizar(c.nome) })))

const sugestoes = computed(() => {
  const q = normalizar(termo.value)
  if (!q) return []
  // quem começa com o que foi digitado vem antes de quem só contém
  const comeca = indice.value.filter((i) => i.chave.startsWith(q))
  const contem = indice.value.filter((i) => !i.chave.startsWith(q) && i.chave.includes(q))
  return [...comeca, ...contem].slice(0, 6).map((i) => i.cidade)
})

function aoDigitar() {
  aberta.value = true
  destaque.value = 0
  if (escolhida.value && termo.value !== escolhida.value.nome) emit('update:modelValue', null)
}

function escolher(cidade: Cidade) {
  termo.value = cidade.nome
  aberta.value = false
  emit('update:modelValue', cidade.id)
}

function escolherAtual() {
  const cidade = sugestoes.value[destaque.value]
  if (cidade) escolher(cidade)
}

function mover(passo: number) {
  if (!sugestoes.value.length) return
  aberta.value = true
  destaque.value = (destaque.value + passo + sugestoes.value.length) % sugestoes.value.length
}

function aoSair(evento: FocusEvent) {
  const destino = evento.relatedTarget as Node | null
  if (!destino || !(evento.currentTarget as HTMLElement).contains(destino)) {
    aberta.value = false
    // Digitou o nome exato e saiu sem tocar na sugestão: aceita.
    if (!escolhida.value) {
      const exata = props.cidades.find((c) => normalizar(c.nome) === normalizar(termo.value))
      if (exata) escolher(exata)
    }
  }
}
</script>

<style scoped>
.cidade {
  position: relative;
  margin-bottom: 16px;
}

.cidade__rotulo {
  display: block;
  margin: 0 0 6px 2px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--chasque-tinta);
}

.cidade__caixa {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  border-radius: 14px;
  background: var(--chasque-papel);
  border: 1.5px solid var(--chasque-neblina);
  color: var(--chasque-tinta-suave);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.cidade__caixa:focus-within {
  border-color: var(--chasque-faixa);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--chasque-faixa) 12%, transparent);
}

.cidade__caixa--escolhida {
  border-color: var(--ion-color-success);
}

.cidade__caixa--escolhida ion-icon {
  color: var(--ion-color-success);
}

.cidade__caixa ion-icon {
  flex: none;
  font-size: 20px;
}

input {
  flex: 1;
  min-width: 0;
  height: 50px;
  border: 0;
  outline: none;
  background: transparent;
  font: inherit;
  font-size: 1rem;
  color: var(--chasque-tinta);
}

input::placeholder {
  color: var(--ion-placeholder-color);
}

.cidade__lista {
  position: absolute;
  z-index: 5;
  left: 0;
  right: 0;
  top: calc(100% + 6px);
  margin: 0;
  padding: 6px;
  list-style: none;
  border-radius: 16px;
  background: var(--chasque-papel);
  border: 1px solid var(--chasque-neblina);
  box-shadow: 0 18px 40px -18px rgba(15, 21, 36, 0.45);
}

.cidade__lista li {
  padding: 12px 12px;
  border-radius: 10px;
  color: var(--chasque-tinta);
  cursor: pointer;
}

.cidade__lista li.destaque,
.cidade__lista li:active {
  background: var(--chasque-neblina);
}

.cidade__nada {
  margin: 8px 2px 0;
  font-size: 0.85rem;
  color: var(--chasque-tinta-suave);
}
</style>
