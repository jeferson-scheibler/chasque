<template>
  <ion-page>
    <faixa titulo="Mapa" :subtitulo="subtitulo" />

    <ion-content :scroll-y="false" class="mapa-conteudo">
      <div ref="caixa" slot="fixed" class="mapa" />

      <div slot="fixed" class="mapa__topo">
        <div class="filtros" role="radiogroup" aria-label="Quais lugares mostrar">
          <button
            v-for="f in FILTROS"
            :key="f.valor"
            type="button"
            role="radio"
            :aria-checked="filtro === f.valor"
            :class="{ ativo: filtro === f.valor }"
            @click="filtro = f.valor"
          >
            <span v-if="f.valor !== 'todos'" class="marca" :class="`marca--${f.valor}`" aria-hidden="true" />
            {{ f.rotulo }}
            <span v-if="contagem[f.valor]" class="num">{{ contagem[f.valor] }}</span>
          </button>
        </div>
      </div>

      <button
        v-show="!escolhido"
        slot="fixed"
        type="button"
        class="localizar"
        :aria-label="localizando ? 'Localizando' : 'Mostrar onde estou'"
        @click="localizar"
      >
        <ion-spinner v-if="localizando" name="crescent" />
        <ion-icon v-else :icon="navigateOutline" aria-hidden="true" />
      </button>

      <div v-if="carregou && contagem.todos === 0" slot="fixed" class="aviso">
        <h2>Seus lugares aparecem aqui</h2>
        <p>Salve um lugar do Instagram ou registre uma visita, e ele ganha um ponto no mapa.</p>
        <router-link class="botao botao--sol botao--compacto" to="/abas/lugares/visita/nova">Registrar visita</router-link>
      </div>

      <transition name="cartao">
        <article v-if="escolhido" slot="fixed" class="cartao cartao-rs" aria-live="polite">
          <button type="button" class="cartao__fechar" aria-label="Fechar" @click="escolher(null)">
            <ion-icon :icon="close" aria-hidden="true" />
          </button>
          <div class="cartao__cabeca">
            <span class="linha__icone" :class="{ 'cartao__icone--visitado': escolhido.tipo === 'visitado' }">
              <ion-icon :icon="iconeDaCategoria(escolhido.categoria)" aria-hidden="true" />
            </span>
            <div class="cartao__texto">
              <h2>{{ escolhido.nome }}</h2>
              <p>{{ [escolhido.categoria_nome, escolhido.cidade].filter(Boolean).join(' em ') || 'Lugar' }}</p>
            </div>
          </div>
          <div class="cartao__estado">
            <template v-if="escolhido.tipo === 'visitado'">
              <sois :model-value="escolhido.nota ?? 0" somente-leitura />
              <span>{{ escolhido.visitas > 1 ? `Você foi ${escolhido.visitas} vezes` : 'Você já foi' }}</span>
            </template>
            <span v-else>Na sua lista para conhecer</span>
          </div>
          <div class="cartao__acoes">
            <router-link class="botao botao--noite botao--compacto" :to="destino(escolhido)">
              {{ escolhido.tipo === 'visitado' ? 'Ver visita' : 'Abrir' }}
            </router-link>
            <a class="botao botao--leve botao--compacto" :href="rota(escolhido)" target="_blank" rel="noopener noreferrer">
              <ion-icon :icon="navigateOutline" aria-hidden="true" />Como chegar
            </a>
          </div>
        </article>
      </transition>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { IonContent, IonIcon, IonPage, IonSpinner, onIonViewDidEnter } from '@ionic/vue'
import { close, navigateOutline } from 'ionicons/icons'
import {
  AttributionControl, addProtocol, LngLatBounds, Map as MapaLibre, setWorkerUrl,
  type AddProtocolAction, type ExpressionSpecification, type GeoJSONSource, type MapLayerMouseEvent,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import urlDoWorker from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { Protocol } from 'pmtiles'
import { computed, onBeforeUnmount, reactive, ref, shallowRef, watch } from 'vue'
import Faixa from '@/components/Faixa.vue'
import Sois from '@/components/Sois.vue'
import { iconeDaCategoria } from '@/categorias'
import { estiloDoMapa } from '@/mapa/estilo'
import { api } from '@/services/api'
import { useSessao } from '@/stores/sessao'
import type { Cidade } from '@/types'

interface Propriedades {
  lugar_id: number
  nome: string
  categoria: string
  categoria_nome: string
  cidade: string
  tipo: 'salvo' | 'visitado'
  salvo_id: number | null
  visita_id: number | null
  visitas: number
  nota: number | null
}
interface Colecao {
  type: 'FeatureCollection'
  features: { type: 'Feature'; geometry: { type: 'Point'; coordinates: [number, number] }; properties: Propriedades }[]
}

type Filtro = 'todos' | 'salvo' | 'visitado'
const FILTROS: { valor: Filtro; rotulo: string }[] = [
  { valor: 'todos', rotulo: 'Todos' },
  { valor: 'salvo', rotulo: 'A conhecer' },
  { valor: 'visitado', rotulo: 'Visitados' },
]
const RS: [[number, number], [number, number]] = [[-57.65, -33.75], [-49.69, -27.08]]
const CAMADAS_CLICAVEIS = ['meus-salvos', 'meus-visitados']

// Uma vez por app: o worker do MapLibre (empacotado pelo Vite) e o leitor de PMTiles.
let preparado = false
function prepararMapLibre() {
  if (preparado) return
  setWorkerUrl(urlDoWorker)
  // mesma assinatura (params, abortController); só o tipo de retorno é descrito de outro jeito
  addProtocol('pmtiles', new Protocol().tilev4 as unknown as AddProtocolAction)
  preparado = true
}

const sessao = useSessao()
const caixa = ref<HTMLDivElement | null>(null)
const mapa = shallowRef<MapaLibre | null>(null)
const dados = shallowRef<Colecao>({ type: 'FeatureCollection', features: [] })
const filtro = ref<Filtro>('todos')
const escolhido = ref<Propriedades | null>(null)
const localizando = ref(false)
const carregou = ref(false)
const eu = ref<[number, number] | null>(null)
const contagem = reactive({ todos: 0, salvo: 0, visitado: 0 })

const subtitulo = computed(() => {
  if (!carregou.value || !contagem.todos) return 'Rio Grande do Sul'
  const partes = []
  if (contagem.salvo) partes.push(`${contagem.salvo} para conhecer`)
  if (contagem.visitado) partes.push(`${contagem.visitado} ${contagem.visitado === 1 ? 'visitado' : 'visitados'}`)
  return partes.join(' e ')
})

const temaEscuro = window.matchMedia('(prefers-color-scheme: dark)')

function cores() {
  const css = getComputedStyle(document.documentElement)
  const v = (nome: string) => css.getPropertyValue(nome).trim()
  return { ocre: v('--chasque-ocre'), faixa: v('--chasque-faixa'), fundo: v('--chasque-fundo'), tinta: v('--chasque-tinta') }
}

function filtroDoTipo(): ExpressionSpecification {
  return filtro.value === 'todos' ? ['literal', true] : ['==', ['get', 'tipo'], filtro.value]
}

function adicionarCamadas(m: MapaLibre) {
  const c = cores()
  const escuro = temaEscuro.matches
  if (!m.getSource('meus')) m.addSource('meus', { type: 'geojson', data: dados.value })
  if (!m.getSource('eu')) m.addSource('eu', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
  // brilho do sol por baixo dos visitados
  m.addLayer({
    id: 'meus-brilho', type: 'circle', source: 'meus',
    filter: ['==', ['get', 'tipo'], 'visitado'],
    paint: { 'circle-color': c.ocre, 'circle-radius': ['interpolate', ['linear'], ['zoom'], 6, 10, 14, 22], 'circle-opacity': 0.28, 'circle-blur': 0.7 },
  })
  m.addLayer({
    id: 'meus-salvos', type: 'circle', source: 'meus',
    filter: ['==', ['get', 'tipo'], 'salvo'],
    paint: {
      'circle-color': escuro ? '#faf6ee' : c.faixa,
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 6, 5, 14, 8.5],
      'circle-stroke-color': escuro ? c.faixa : '#faf6ee',
      'circle-stroke-width': 2.5,
    },
  })
  m.addLayer({
    id: 'meus-visitados', type: 'circle', source: 'meus',
    filter: ['==', ['get', 'tipo'], 'visitado'],
    paint: {
      'circle-color': c.ocre,
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 6, 6, 14, 10],
      'circle-stroke-color': escuro ? '#0f1524' : '#faf6ee',
      'circle-stroke-width': 2.5,
    },
  })
  m.addLayer({
    id: 'meus-escolhido', type: 'circle', source: 'meus',
    filter: ['==', ['get', 'lugar_id'], escolhido.value?.lugar_id ?? -1],
    paint: { 'circle-color': 'rgba(0,0,0,0)', 'circle-radius': 17, 'circle-stroke-color': c.ocre, 'circle-stroke-width': 3 },
  })
  m.addLayer({
    id: 'meus-nomes', type: 'symbol', source: 'meus', minzoom: 11,
    layout: {
      'text-field': ['get', 'nome'], 'text-font': ['Noto Sans Medium'], 'text-size': 12.5,
      'text-offset': [0, 1.3], 'text-anchor': 'top', 'text-max-width': 9, 'text-optional': true,
    },
    paint: { 'text-color': c.tinta, 'text-halo-color': escuro ? '#0f1524' : '#faf6ee', 'text-halo-width': 1.8 },
  })
  m.addLayer({
    id: 'eu', type: 'circle', source: 'eu',
    paint: { 'circle-color': '#3d7be0', 'circle-radius': 7, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 3 },
  })
  aplicarFiltro()
}

function aplicarFiltro() {
  const m = mapa.value
  if (!m || !m.getLayer('meus-salvos')) return
  const tipo = filtroDoTipo()
  m.setFilter('meus-salvos', ['all', ['==', ['get', 'tipo'], 'salvo'], tipo])
  m.setFilter('meus-visitados', ['all', ['==', ['get', 'tipo'], 'visitado'], tipo])
  m.setFilter('meus-brilho', ['all', ['==', ['get', 'tipo'], 'visitado'], tipo])
  m.setFilter('meus-nomes', tipo)
}

function enquadrar(m: MapaLibre) {
  const pontos = dados.value.features.map((f) => f.geometry.coordinates)
  const margem = { top: 96, bottom: 150, left: 40, right: 40 }
  if (pontos.length) {
    const caixaDosPontos = pontos.reduce((b, p) => b.extend(p), new LngLatBounds(pontos[0], pontos[0]))
    m.fitBounds(caixaDosPontos, { padding: margem, maxZoom: 13.5, duration: 0 })
    return
  }
  // sem lugares: abre na cidade da pessoa, ou no RS inteiro
  void (async () => {
    const nome = sessao.usuario?.cidade_base?.trim().toLowerCase()
    if (nome) {
      const cidade = (await api<Cidade[]>('/cidades/')).find((c) => c.nome.toLowerCase() === nome)
      if (cidade) {
        m.jumpTo({ center: [cidade.lng, cidade.lat], zoom: 11 })
        return
      }
    }
    m.fitBounds(RS, { padding: 20, duration: 0 })
  })()
}

async function carregarLugares() {
  try {
    dados.value = await api<Colecao>('/mapa/')
  } catch {
    return
  }
  const f = dados.value.features
  contagem.todos = f.length
  contagem.salvo = f.filter((x) => x.properties.tipo === 'salvo').length
  contagem.visitado = f.filter((x) => x.properties.tipo === 'visitado').length
  carregou.value = true
  const fonte = mapa.value?.getSource('meus') as GeoJSONSource | undefined
  fonte?.setData(dados.value)
}

function criarMapa() {
  prepararMapLibre()
  const m = new MapaLibre({
    container: caixa.value!,
    style: estiloDoMapa(temaEscuro.matches, `${location.origin}/tiles/rs.pmtiles`),
    bounds: RS,
    attributionControl: false,
    maxBounds: [[-60.5, -35.5], [-46.5, -25]],
    dragRotate: false,
    pitchWithRotate: false,
  })
  m.touchZoomRotate.disableRotation()
  m.addControl(new AttributionControl({ compact: true }), 'bottom-left')
  m.on('style.load', () => adicionarCamadas(m))
  m.once('load', () => enquadrar(m))
  m.on('click', (e) => {
    const [alvo] = m.queryRenderedFeatures(e.point, { layers: CAMADAS_CLICAVEIS.filter((id) => m.getLayer(id)) })
    escolher(alvo ? (alvo.properties as unknown as Propriedades) : null)
  })
  for (const camada of CAMADAS_CLICAVEIS) {
    m.on('mouseenter', camada, (_: MapLayerMouseEvent) => { m.getCanvas().style.cursor = 'pointer' })
    m.on('mouseleave', camada, () => { m.getCanvas().style.cursor = '' })
  }
  mapa.value = m
}

function escolher(p: Propriedades | null) {
  escolhido.value = p
  mapa.value?.setFilter('meus-escolhido', ['==', ['get', 'lugar_id'], p?.lugar_id ?? -1])
  if (p) {
    const f = dados.value.features.find((x) => x.properties.lugar_id === p.lugar_id)
    if (f) mapa.value?.easeTo({ center: f.geometry.coordinates, offset: [0, -60], duration: 450 })
  }
}

function destino(p: Propriedades) {
  return p.tipo === 'visitado' && p.visita_id ? `/abas/lugares/visita/${p.visita_id}` : `/abas/lugares/salvo/${p.salvo_id}`
}

function rota(p: Propriedades) {
  const f = dados.value.features.find((x) => x.properties.lugar_id === p.lugar_id)
  const [lng, lat] = f?.geometry.coordinates ?? [0, 0]
  // Só um link para o app de mapas do celular; nada do Google é guardado.
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
}

function localizar() {
  if (!('geolocation' in navigator)) return
  localizando.value = true
  // Só pede a posição quando a pessoa toca no botão; nada roda em segundo plano.
  navigator.geolocation.getCurrentPosition(
    (p) => {
      localizando.value = false
      eu.value = [p.coords.longitude, p.coords.latitude]
      const fonte = mapa.value?.getSource('eu') as GeoJSONSource | undefined
      fonte?.setData({ type: 'Feature', geometry: { type: 'Point', coordinates: eu.value }, properties: {} })
      mapa.value?.flyTo({ center: eu.value, zoom: 13, duration: 900 })
    },
    () => { localizando.value = false },
    { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
  )
}

function trocarTema() {
  const m = mapa.value
  if (!m) return
  m.setStyle(estiloDoMapa(temaEscuro.matches, `${location.origin}/tiles/rs.pmtiles`))
}

watch(filtro, aplicarFiltro)
temaEscuro.addEventListener('change', trocarTema)

onIonViewDidEnter(async () => {
  if (!mapa.value) criarMapa()
  else mapa.value.resize()
  await carregarLugares()
  if (mapa.value?.loaded()) enquadrar(mapa.value)
})

onBeforeUnmount(() => {
  temaEscuro.removeEventListener('change', trocarTema)
  mapa.value?.remove()
})
</script>

<style scoped>
.mapa-conteudo {
  --background: var(--chasque-fundo);
}

.mapa {
  position: absolute;
  inset: 0;
}

.mapa__topo {
  position: absolute;
  top: 34px;
  left: 12px;
  right: 12px;
  display: flex;
  gap: 8px;
  align-items: flex-start;
  pointer-events: none;
}

.filtros {
  display: flex;
  gap: 6px;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
  pointer-events: auto;
}

.filtros::-webkit-scrollbar {
  display: none;
}

.filtros button,
.localizar {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  padding: 0 11px;
  border: 0;
  border-radius: 999px;
  background: var(--chasque-papel);
  color: var(--chasque-tinta);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  box-shadow: 0 6px 18px -8px rgba(15, 21, 36, 0.45);
  transition: background-color 0.18s ease, color 0.18s ease;
}

.filtros button.ativo {
  background: var(--chasque-faixa);
  color: var(--chasque-faixa-texto);
}

@media (prefers-color-scheme: dark) {
  .filtros button.ativo {
    background: var(--chasque-faixa-texto);
    color: var(--chasque-faixa);
  }
}

.num {
  min-width: 20px;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--chasque-neblina);
  color: var(--chasque-tinta);
  font-size: 0.75rem;
  text-align: center;
}

.ativo .num {
  background: var(--chasque-faixa-vidro);
  color: inherit;
}

.marca {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  border: 2px solid var(--chasque-papel);
  box-shadow: 0 0 0 1px var(--chasque-neblina);
}

.marca--visitado {
  background: var(--chasque-ocre);
}

.marca--salvo {
  background: var(--chasque-faixa);
}

@media (prefers-color-scheme: dark) {
  .marca--salvo {
    background: #faf6ee;
  }
}

.localizar {
  position: absolute;
  right: 12px;
  bottom: 52px;
  width: 46px;
  height: 46px;
  padding: 0;
  justify-content: center;
}

.localizar ion-icon {
  font-size: 21px;
  color: var(--chasque-ocre);
}

.localizar ion-spinner {
  width: 18px;
  height: 18px;
  color: var(--chasque-ocre);
}

.aviso {
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 58px;
  padding: 20px;
  border-radius: 22px;
  background: var(--chasque-papel);
  box-shadow: 0 18px 40px -18px rgba(15, 21, 36, 0.5);
  text-align: center;
}

.aviso h2 {
  margin: 0 0 6px;
  font-size: 1.15rem;
  font-weight: 650;
  color: var(--chasque-tinta);
}

.aviso p {
  margin: 0 0 14px;
  color: var(--chasque-tinta-suave);
  font-size: 0.92rem;
}

.cartao {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 52px;
  padding: 26px 18px 16px;
  --cartao-rs-traco: var(--chasque-papel);
  filter: drop-shadow(0 14px 22px rgba(15, 21, 36, 0.4));
}

.cartao__fechar {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 50%;
  background: var(--chasque-neblina);
  color: var(--chasque-tinta);
  display: grid;
  place-items: center;
  font-size: 18px;
}

.cartao__cabeca {
  display: flex;
  gap: 14px;
  align-items: center;
  padding-right: 36px;
}

.cartao__icone--visitado {
  background: var(--chasque-ocre);
  color: var(--chasque-sobre-ocre);
}

.cartao__texto h2 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 650;
  line-height: 1.2;
  color: var(--chasque-tinta);
}

.cartao__texto p {
  margin: 3px 0 0;
  font-size: 0.88rem;
  color: var(--chasque-tinta-suave);
}

.cartao__estado {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 14px 0 16px;
  font-size: 0.9rem;
  color: var(--chasque-tinta-suave);
}

.cartao__acoes {
  display: flex;
  gap: 10px;
}

.cartao__acoes .botao {
  flex: 1;
  padding: 0 12px;
  white-space: nowrap;
}

.cartao-enter-active,
.cartao-leave-active {
  transition: transform 0.28s cubic-bezier(0.2, 0.8, 0.2, 1), opacity 0.2s ease;
}

.cartao-enter-from,
.cartao-leave-to {
  transform: translateY(24px);
  opacity: 0;
}

/* atribuição do OSM acima da borda da barra de abas */
:deep(.maplibregl-ctrl-bottom-left) {
  bottom: 22px;
}

:deep(.maplibregl-ctrl-attrib) {
  background: color-mix(in srgb, var(--chasque-papel) 85%, transparent);
  color: var(--chasque-tinta-suave);
}

:deep(.maplibregl-ctrl-attrib a) {
  color: var(--chasque-tinta-suave);
}

@media (prefers-color-scheme: dark) {
  :deep(.maplibregl-ctrl-attrib-button) {
    filter: invert(1);
  }
}
</style>
