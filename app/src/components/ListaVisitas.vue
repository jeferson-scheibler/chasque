<template>
  <div class="visitas">
    <div v-if="total > 0 || termo" class="visitas__busca">
      <ion-icon :icon="searchOutline" aria-hidden="true" />
      <input
        v-model="termo"
        type="search"
        enterkeyhint="search"
        placeholder="Buscar por motivo, lugar ou cidade"
        aria-label="Buscar nas visitas"
        @input="agendarBusca"
      />
    </div>

    <div v-if="carregando && visitas.length === 0" class="ion-padding ion-text-center"><ion-spinner name="crescent" /></div>

    <vazio
      v-else-if="visitas.length === 0 && !termo"
      pose="caminho"
      titulo="Guarde por que você gostou"
      texto="Registre o lugar onde você foi, como foi e o que fez diferença. É assim que o Chasque aprende o seu gosto."
    >
      <router-link class="botao botao--sol botao--compacto" to="/abas/lugares/visita/nova">
        <ion-icon :icon="footstepsOutline" aria-hidden="true" />Registrar visita
      </router-link>
    </vazio>

    <p v-else-if="visitas.length === 0" class="visitas__nada">Nenhuma visita com "{{ termo.trim() }}".</p>

    <ul v-else class="linhas">
      <li v-for="visita in visitas" :key="visita.id">
        <router-link :to="`/abas/lugares/visita/${visita.id}`" class="linha visita">
          <span class="linha__icone"><ion-icon :icon="iconeDaCategoria(visita.lugar.categoria)" aria-hidden="true" /></span>
          <span class="linha__texto">
            <span class="visita__topo">
              <span class="linha__titulo">{{ visita.lugar.nome }}</span>
              <sois :model-value="visita.nota" somente-leitura />
            </span>
            <span class="linha__meta">
              <ion-icon v-if="!visita.privado" :icon="peopleOutline" class="compartilhada" aria-label="Pessoas de confiança veem" />
              {{ meta(visita) }}
            </span>
            <span v-if="visita.tags.length" class="visita__motivos">
              <span v-for="slug in visita.tags.slice(0, 3)" :key="slug" :class="{ achado: achou(slug) }">{{ motivos.nome(slug) }}</span>
              <span v-if="visita.tags.length > 3" class="mais">+{{ visita.tags.length - 3 }}</span>
            </span>
            <span v-else-if="visita.motivo" class="visita__texto">{{ visita.motivo }}</span>
          </span>
        </router-link>
      </li>
    </ul>

    <ion-infinite-scroll :disabled="!temMais" @ion-infinite="carregarMais($event)">
      <ion-infinite-scroll-content />
    </ion-infinite-scroll>
  </div>
</template>

<script setup lang="ts">
import {
  IonIcon, IonInfiniteScroll, IonInfiniteScrollContent, IonSpinner, type InfiniteScrollCustomEvent,
} from '@ionic/vue'
import { footstepsOutline, peopleOutline, searchOutline } from 'ionicons/icons'
import { onMounted, ref } from 'vue'
import Sois from '@/components/Sois.vue'
import Vazio from '@/components/Vazio.vue'
import { iconeDaCategoria } from '@/categorias'
import { api } from '@/services/api'
import { useMotivos } from '@/stores/motivos'
import type { Pagina, Registro } from '@/types'

const OCASIAO: Record<string, string> = {
  sozinho: 'sozinho', casal: 'em casal', familia: 'com a família', amigos: 'com amigos', trabalho: 'a trabalho',
}

const motivos = useMotivos()
const visitas = ref<Registro[]>([])
const total = ref(0)
const pagina = ref(1)
const temMais = ref(false)
const carregando = ref(false)
const termo = ref('')

let espera: ReturnType<typeof setTimeout> | undefined
let ultima = 0

const formatoData = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short' })

function meta(v: Registro) {
  const quando = formatoData.format(new Date(`${v.visitado_em}T12:00:00`)).replace('.', '')
  return [v.lugar.cidade, `${quando}, ${OCASIAO[v.ocasiao]}`].filter(Boolean).join('. ')
}

function normalizar(t: string) {
  return t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

/** Destaca o motivo que bateu com a busca. */
function achou(slug: string) {
  const q = normalizar(termo.value.trim())
  return q.length >= 2 && normalizar(motivos.nome(slug)).includes(q)
}

async function buscarPagina(n: number) {
  const q = termo.value.trim()
  const r = await api<Pagina<Registro>>(`/registros/?page=${n}${q ? `&q=${encodeURIComponent(q)}` : ''}`)
  temMais.value = r.next !== null
  pagina.value = n
  if (!q) total.value = r.count
  return r.results
}

async function recarregar() {
  const esta = ++ultima
  carregando.value = true
  try {
    await motivos.carregar()
    const resultado = await buscarPagina(1)
    if (esta === ultima) visitas.value = resultado
  } catch {
    // mantém a lista anterior se a rede falhar
  } finally {
    if (esta === ultima) carregando.value = false
  }
}

function agendarBusca() {
  clearTimeout(espera)
  espera = setTimeout(recarregar, 280)
}

async function carregarMais(evento: InfiniteScrollCustomEvent) {
  try {
    visitas.value.push(...(await buscarPagina(pagina.value + 1)))
  } finally {
    await evento.target.complete()
  }
}

onMounted(recarregar)
defineExpose({ recarregar })
</script>

<style scoped>
.visitas__busca {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 16px 6px;
  padding: 0 14px;
  height: 50px;
  border-radius: 16px;
  background: var(--chasque-papel);
  border: 1.5px solid var(--chasque-neblina);
  color: var(--chasque-tinta-suave);
}

.visitas__busca:focus-within {
  border-color: var(--chasque-faixa);
}

.visitas__busca ion-icon {
  font-size: 20px;
  flex: none;
}

.visitas__busca input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  font: inherit;
  font-size: 1rem;
  color: var(--chasque-tinta);
}

.visitas__nada {
  margin: 24px 20px;
  color: var(--chasque-tinta-suave);
}

.visita {
  align-items: flex-start;
}

.visita__topo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.visita__topo .linha__titulo {
  min-width: 0;
}

.compartilhada {
  font-size: 14px;
  vertical-align: -2px;
  margin-right: 2px;
  color: var(--chasque-ocre);
}

.visita__motivos {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.visita__motivos span {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--chasque-neblina);
  color: var(--chasque-tinta);
  font-size: 0.78rem;
  font-weight: 500;
}

.visita__motivos span.achado {
  background: var(--chasque-ocre);
  color: var(--chasque-sobre-ocre);
}

.visita__motivos .mais {
  background: transparent;
  color: var(--chasque-tinta-suave);
}

.visita__texto {
  display: block;
  margin-top: 6px;
  font-size: 0.875rem;
  color: var(--chasque-tinta-suave);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
