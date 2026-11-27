<template>
  <div class="qual">
    <template v-if="!novo && (carregando || meus.length)">
      <h2 class="secao-titulo">{{ titulo }}</h2>
      <p class="secao-apoio">Se for de um lugar que você já salvou ou visitou, o link entra junto com os outros.</p>

      <div v-if="meus.length > POUCOS || termo" class="qual__filtro">
        <ion-icon :icon="searchOutline" aria-hidden="true" />
        <input v-model="termo" type="search" autocomplete="off" placeholder="Filtrar seus lugares" aria-label="Filtrar seus lugares" />
      </div>

      <div v-if="carregando" class="ion-padding ion-text-center"><ion-spinner name="crescent" /></div>
      <ul v-else-if="visiveis.length" class="linhas qual__meus">
        <li v-for="(lugar, i) in visiveis" :key="lugar.id" :style="{ '--i': i }">
          <button type="button" class="linha" @click="emit('escolher', lugar)">
            <span class="linha__icone"><ion-icon :icon="iconeDaCategoria(lugar.categoria)" aria-hidden="true" /></span>
            <span class="linha__texto">
              <span class="linha__titulo">{{ lugar.nome }}</span>
              <span class="linha__meta">{{ metaDoLugar(lugar) }}</span>
            </span>
            <span class="qual__esse">Esse</span>
          </button>
        </li>
      </ul>
      <p v-else class="qual__nada">Nenhum dos seus lugares tem esse nome.</p>

      <button v-if="!termo && meus.length > POUCOS && !todos" type="button" class="botao botao--texto qual__mais" @click="todos = true">
        Ver todos os {{ meus.length }}
      </button>

      <button type="button" class="qual__novo" @click="novo = true">
        <span class="qual__sol" aria-hidden="true"><ion-icon :icon="addOutline" /></span>
        <span class="linha__texto">
          <span class="linha__titulo">Iniciar um novo Chasque</span>
          <span class="linha__meta qual__novo-meta">Lugar que ainda não está na sua lista</span>
        </span>
        <ion-icon :icon="chevronForward" class="linha__seta" aria-hidden="true" />
      </button>
    </template>

    <template v-else>
      <h2 class="secao-titulo">{{ meus.length ? 'Novo Chasque: qual é o lugar?' : titulo }}</h2>
      <p class="secao-apoio">Busque pelo nome. A base tem os lugares do Rio Grande do Sul.</p>
      <busca-lugar :sugestao="sugestao" @escolher="emit('escolher', $event)" />
      <button v-if="meus.length" type="button" class="botao botao--texto qual__voltar" @click="novo = false">
        Voltar para os seus lugares
      </button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { IonIcon, IonSpinner } from '@ionic/vue'
import { addOutline, chevronForward, searchOutline } from 'ionicons/icons'
import { computed, onMounted, ref } from 'vue'
import BuscaLugar from '@/components/BuscaLugar.vue'
import { iconeDaCategoria } from '@/categorias'
import { api } from '@/services/api'
import { resumoDoLugar, type Lugar, type MeuLugar } from '@/types'

const POUCOS = 5

const props = defineProps<{ titulo: string; sugestao?: string; ignorar?: number | null }>()
const emit = defineEmits<{ escolher: [lugar: Lugar] }>()

const meus = ref<MeuLugar[]>([])
const carregando = ref(true)
const novo = ref(false)
const todos = ref(false)
const termo = ref('')

function semAcento(texto: string) {
  return texto.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
}

const visiveis = computed(() => {
  const lista = meus.value.filter((l) => l.id !== props.ignorar)
  if (termo.value.trim()) {
    const t = semAcento(termo.value.trim())
    return lista.filter((l) => semAcento(l.nome).includes(t))
  }
  return todos.value ? lista : lista.slice(0, POUCOS)
})

function metaDoLugar(lugar: MeuLugar) {
  const partes = [resumoDoLugar(lugar)]
  if (lugar.links) partes.push(lugar.links === 1 ? '1 link salvo' : `${lugar.links} links salvos`)
  if (lugar.visitado) partes.push('visitado')
  return partes.filter(Boolean).join(', ')
}

onMounted(async () => {
  try {
    meus.value = await api<MeuLugar[]>('/meus-lugares/')
  } catch {
    meus.value = []
  } finally {
    carregando.value = false
  }
})
</script>

<style scoped>
.qual__filtro {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 4px 16px 8px;
  padding: 0 14px;
  height: 44px;
  border-radius: 14px;
  background: var(--chasque-papel);
  border: 1px solid var(--chasque-neblina);
  color: var(--chasque-tinta-suave);
}

.qual__filtro input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  font: inherit;
  color: var(--chasque-tinta);
  outline: none;
}

/* cada lugar chega um pouco depois do anterior, como cartas na mesa */
.qual__meus li {
  animation: chegar 0.35s ease-out both;
  animation-delay: calc(var(--i) * 45ms);
}

.qual__esse {
  flex: none;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--chasque-neblina);
  color: var(--chasque-tinta);
  font-size: 0.82rem;
  font-weight: 600;
}

.qual__nada {
  margin: 8px 20px;
  color: var(--chasque-tinta-suave);
}

.qual__mais,
.qual__voltar {
  width: auto;
  margin: 4px 20px 0;
  padding: 0;
  color: var(--chasque-tinta-suave);
  text-decoration: underline;
  text-underline-offset: 4px;
}

.qual__novo {
  display: flex;
  align-items: center;
  gap: 14px;
  width: calc(100% - 32px);
  margin: 18px 16px 0;
  padding: 14px 16px;
  border: 1.5px dashed color-mix(in srgb, var(--chasque-ocre) 70%, transparent);
  border-radius: 18px;
  background: color-mix(in srgb, var(--chasque-ocre) 10%, var(--chasque-papel));
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: transform 0.15s ease;
}

.qual__novo:active {
  transform: scale(0.98);
}

.qual__novo-meta {
  white-space: normal;
}

.qual__sol {
  flex: none;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 22px;
  color: var(--chasque-sobre-ocre);
  background: var(--chasque-ocre);
}

@keyframes chegar {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .qual__meus li {
    animation: none;
  }
}
</style>
