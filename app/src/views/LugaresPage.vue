<template>
  <ion-page>
    <faixa titulo="Meus lugares">
      <div class="alternador" role="tablist" aria-label="Lista">
        <button
          v-for="opcao in OPCOES"
          :key="opcao.valor"
          role="tab"
          type="button"
          :aria-selected="aba === opcao.valor"
          :class="{ ativo: aba === opcao.valor }"
          @click="aba = opcao.valor"
        >
          {{ opcao.rotulo }}
        </button>
      </div>
    </faixa>

    <ion-content class="vale">
      <template v-if="aba === 'salvos'">
        <ion-refresher slot="fixed" @ion-refresh="recarregar($event)">
          <ion-refresher-content />
        </ion-refresher>

        <div v-if="carregando && salvos.length === 0" class="esqueleto" aria-label="Carregando">
          <div v-for="n in 4" :key="n" class="esqueleto__linha">
            <ion-skeleton-text :animated="true" class="esqueleto__icone" />
            <div><ion-skeleton-text :animated="true" style="width: 60%" /><ion-skeleton-text :animated="true" style="width: 40%" /></div>
          </div>
        </div>

        <vazio
          v-else-if="salvos.length === 0"
          titulo="Comece pelo que você viu no Instagram"
          texto="Compartilhe um post ou reel com o Chasque, ou copie o link e toque no sol."
        >
          <button class="botao botao--sol botao--compacto" type="button" @click="adicionar.abrir()">
            <ion-icon :icon="logoInstagram" aria-hidden="true" />Salvar do Instagram
          </button>
        </vazio>

        <template v-else>
          <section v-if="pendentes.length" class="pendentes">
            <h2 class="secao-titulo">Falta dizer qual é o lugar</h2>
            <p class="secao-apoio">Links que você salvou e ainda não ligou a um lugar.</p>
            <router-link
              v-for="salvo in pendentes"
              :key="salvo.id"
              :to="`/abas/lugares/salvo/${salvo.id}`"
              class="bilhete"
            >
              <ion-icon :icon="logoInstagram" aria-hidden="true" class="bilhete__icone" />
              <span class="linha__texto">
                <span class="linha__titulo">{{ salvo.perfil ? `@${salvo.perfil}` : NOME_DO_TIPO[salvo.tipo] }}</span>
                <span class="linha__meta">{{ salvo.texto || `Salvo em ${dataCurta(salvo.criado_em)}` }}</span>
              </span>
              <span class="bilhete__acao">Identificar</span>
            </router-link>
          </section>

          <section v-if="identificados.length">
            <h2 class="secao-titulo">Quero conhecer</h2>
            <ul class="linhas">
              <li v-for="salvo in identificados" :key="salvo.id">
                <router-link :to="`/abas/lugares/salvo/${salvo.id}`" class="linha">
                  <span class="linha__icone"><ion-icon :icon="iconeDaCategoria(salvo.lugar!.categoria)" aria-hidden="true" /></span>
                  <span class="linha__texto">
                    <span class="linha__titulo">{{ salvo.lugar!.nome }}</span>
                    <span class="linha__meta">{{ resumoDoLugar(salvo.lugar!) || NOME_DO_TIPO[salvo.tipo] }}</span>
                  </span>
                  <span v-if="salvo.visitado" class="visitado">Visitado</span>
                  <ion-icon :icon="chevronForward" class="linha__seta" aria-hidden="true" />
                </router-link>
              </li>
            </ul>
          </section>
        </template>

        <ion-infinite-scroll :disabled="!temMais" @ion-infinite="carregarMais($event)">
          <ion-infinite-scroll-content />
        </ion-infinite-scroll>
      </template>

      <lista-visitas v-else ref="listaVisitas" />
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import {
  IonContent, IonIcon, IonInfiniteScroll, IonInfiniteScrollContent, IonPage, IonRefresher, IonRefresherContent,
  IonSkeletonText, onIonViewWillEnter, type InfiniteScrollCustomEvent, type RefresherCustomEvent,
} from '@ionic/vue'
import { chevronForward, logoInstagram } from 'ionicons/icons'
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import Faixa from '@/components/Faixa.vue'
import ListaVisitas from '@/components/ListaVisitas.vue'
import Vazio from '@/components/Vazio.vue'
import { iconeDaCategoria } from '@/categorias'
import { api } from '@/services/api'
import { useAdicionar } from '@/stores/adicionar'
import { NOME_DO_TIPO, resumoDoLugar, type Pagina, type Salvo } from '@/types'

const OPCOES = [
  { valor: 'salvos', rotulo: 'Quero conhecer' },
  { valor: 'visitados', rotulo: 'Visitados' },
] as const

const adicionar = useAdicionar()
const route = useRoute()
const listaVisitas = ref<InstanceType<typeof ListaVisitas> | null>(null)

const aba = ref<'salvos' | 'visitados'>('salvos')
const salvos = ref<Salvo[]>([])
const pagina = ref(1)
const temMais = ref(false)
const carregando = ref(false)

const pendentes = computed(() => salvos.value.filter((s) => !s.lugar))
const identificados = computed(() => salvos.value.filter((s) => s.lugar))

const formatoData = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short' })
function dataCurta(iso: string) {
  return formatoData.format(new Date(iso)).replace('.', '')
}

async function buscarPagina(n: number) {
  const r = await api<Pagina<Salvo>>(`/salvos/?page=${n}`)
  temMais.value = r.next !== null
  pagina.value = n
  return r.results
}

async function recarregar(evento?: RefresherCustomEvent) {
  carregando.value = true
  try {
    salvos.value = await buscarPagina(1)
  } catch {
    // mantém a lista anterior se a rede falhar
  } finally {
    carregando.value = false
    await evento?.target.complete()
  }
}

async function carregarMais(evento: InfiniteScrollCustomEvent) {
  try {
    salvos.value.push(...(await buscarPagina(pagina.value + 1)))
  } finally {
    await evento.target.complete()
  }
}

onIonViewWillEnter(() => {
  // Depois de registrar uma visita, a tela volta com ?aba=visitados.
  if (route.query.aba === 'visitados') aba.value = 'visitados'
  void recarregar()
  void listaVisitas.value?.recarregar()
})
</script>

<style scoped>
.alternador {
  /* deixa o canto direito livre para as araucárias */
  max-width: calc(100% - 104px);
  display: flex;
  padding: 4px;
  border-radius: 999px;
  background: var(--chasque-faixa-vidro);
}

.alternador button {
  flex: 1;
  height: 38px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--chasque-faixa-suave);
  font: inherit;
  font-weight: 600;
  font-size: 0.92rem;
  transition: background-color 0.25s ease, color 0.25s ease;
}

.alternador button.ativo {
  background: var(--chasque-faixa-texto);
  color: var(--chasque-faixa);
}

.visitado {
  flex: none;
  padding: 5px 10px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--ion-color-success) 16%, transparent);
  color: var(--ion-color-success);
  font-size: 0.75rem;
  font-weight: 700;
}

.pendentes {
  padding-bottom: 6px;
}

/* Um link sem lugar é um recado pela metade: borda tracejada até ser identificado. */
.bilhete {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 10px 16px 0;
  padding: 14px 14px 14px 16px;
  border: 1.5px dashed color-mix(in srgb, var(--chasque-ocre) 70%, transparent);
  border-radius: 18px;
  background: color-mix(in srgb, var(--chasque-ocre) 7%, var(--chasque-fundo));
  color: inherit;
  text-decoration: none;
  transition: transform 0.15s ease;
}

.bilhete:active {
  transform: scale(0.985);
}

.bilhete__icone {
  flex: none;
  font-size: 24px;
  color: var(--chasque-ocre);
}

.bilhete__acao {
  flex: none;
  padding: 8px 12px;
  border-radius: 999px;
  background: var(--chasque-ocre);
  color: var(--chasque-sobre-ocre);
  font-size: 0.8rem;
  font-weight: 700;
}

.esqueleto {
  padding: 8px 20px;
}

.esqueleto__linha {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 12px 0;
}

.esqueleto__linha > div {
  flex: 1;
}

.esqueleto__icone {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  margin: 0;
}

ion-skeleton-text {
  --background: var(--chasque-neblina);
  --background-rgb: 235, 228, 213;
  border-radius: 6px;
}
</style>
