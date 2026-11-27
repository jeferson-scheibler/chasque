<template>
  <ion-page>
    <faixa :titulo="roteiro ? tituloDoRoteiro(roteiro) : 'Roteiro'" :subtitulo="subtitulo" voltar="/abas/sugestoes" />

    <ion-content class="vale">
      <div v-if="carregando" class="ion-padding ion-text-center"><ion-spinner name="crescent" /></div>

      <vazio
        v-else-if="!roteiro"
        ilustracao="gaucho"
        titulo="Esse roteiro já passou"
        texto="O dia pode ter ficado ocupado na agenda ou o fim de semana já foi. Os próximos aparecem em Sugestões."
      >
        <router-link class="botao botao--noite botao--compacto" to="/abas/sugestoes" replace>Ver sugestões</router-link>
      </vazio>

      <template v-else>
        <p class="abertura">
          Juntamos {{ contagem }}, perto um do outro, na ordem de um dia de passeio.
        </p>

        <ol class="trilha" :style="{ '--paradas': roteiro.paradas.length }">
          <li v-for="(p, i) in roteiro.paradas" :key="p.lugar.id" class="parada" :style="{ '--i': i }">
            <p v-if="p.km_da_anterior !== null" class="parada__caminho">{{ distancia(p.km_da_anterior) }}</p>
            <span class="parada__marco" aria-hidden="true">
              <ion-icon :icon="ICONE_DO_MOMENTO[p.momento]" />
            </span>
            <div class="parada__corpo">
              <p class="parada__momento">{{ NOME_DO_MOMENTO[p.momento] }}</p>
              <component
                :is="p.salvo_id ? 'router-link' : 'div'"
                :to="p.salvo_id ? `/abas/lugares/salvo/${p.salvo_id}` : undefined"
                class="parada__cartao cartao-rs"
              >
                <span class="linha__icone"><ion-icon :icon="iconeDaCategoria(p.lugar.categoria)" aria-hidden="true" /></span>
                <span class="linha__texto">
                  <span class="linha__titulo">{{ p.lugar.nome }}</span>
                  <span class="linha__meta">{{ metaDaParada(p) }}</span>
                </span>
                <span v-if="!p.salvo" class="parada__origem">Sugestão</span>
              </component>
            </div>
          </li>
        </ol>

        <div class="acoes">
          <a class="botao botao--sol" :href="linkDoMapa" target="_blank" rel="noopener noreferrer">
            <ion-icon :icon="navigateOutline" aria-hidden="true" />Abrir o caminho no mapa
          </a>
          <button type="button" class="botao botao--texto" @click="dispensar">Agora não</button>
        </div>
        <p class="nota">
          Horários do OpenStreetMap: confira antes de sair. Paradas marcadas como sugestão vêm das Sugestões do Chasque.
        </p>
      </template>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { IonContent, IonIcon, IonPage, IonSpinner, toastController } from '@ionic/vue'
import { cafeOutline, moonOutline, navigateOutline, restaurantOutline, sunnyOutline } from 'ionicons/icons'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Faixa from '@/components/Faixa.vue'
import Vazio from '@/components/Vazio.vue'
import { iconeDaCategoria } from '@/categorias'
import { api } from '@/services/api'
import { quandoDoRoteiro, tituloDoRoteiro, useRoteiros } from '@/stores/roteiros'
import { NOME_DO_MOMENTO, resumoDoLugar, type Momento, type Parada, type Roteiro } from '@/types'

const ICONE_DO_MOMENTO: Record<Momento, string> = {
  manha: cafeOutline,
  almoco: restaurantOutline,
  tarde: sunnyOutline,
  noite: moonOutline,
}

const route = useRoute()
const router = useRouter()
const roteiros = useRoteiros()
const roteiro = ref<Roteiro | null>(null)
const carregando = ref(true)

const subtitulo = computed(() => (roteiro.value ? `Agenda livre ${quandoDoRoteiro(roteiro.value.dia)}` : undefined))
const contagem = computed(() => {
  const n = roteiro.value?.paradas.length ?? 0
  const meus = roteiro.value?.paradas.filter((p) => p.salvo).length ?? 0
  if (meus === n) return `${n} lugares que você salvou`
  return `${meus === 1 ? '1 lugar que você salvou' : `${meus} lugares que você salvou`} e ${n - meus === 1 ? 'uma sugestão' : `${n - meus} sugestões`}`
})

// Google Maps monta o caminho com as paradas na ordem do roteiro
const linkDoMapa = computed(() => {
  const paradas = roteiro.value?.paradas ?? []
  if (!paradas.length) return '#'
  const ponto = (p: Parada) => `${p.lugar.lat},${p.lugar.lng}`
  const url = new URL('https://www.google.com/maps/dir/')
  url.searchParams.set('api', '1')
  url.searchParams.set('destination', ponto(paradas[paradas.length - 1]))
  if (paradas.length > 1) url.searchParams.set('waypoints', paradas.slice(0, -1).map(ponto).join('|'))
  return url.toString()
})

function distancia(km: number) {
  if (km < 1) return `${Math.max(100, Math.round((km * 1000) / 100) * 100)} m até a próxima`
  return `${km.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} km até a próxima`
}

function metaDaParada(p: Parada) {
  const resumo = resumoDoLugar(p.lugar)
  const horario = p.horario ? `aberto ${p.horario}` : ''
  return [resumo, horario].filter(Boolean).join(', ') || 'Lugar'
}

async function dispensar() {
  if (!roteiro.value) return
  const id = roteiro.value.id
  try {
    await api(`/roteiros/${id}/`, { method: 'DELETE' })
    roteiros.remover(id)
    await router.replace('/abas/sugestoes')
    const toast = await toastController.create({ message: 'Roteiro guardado na gaveta. Fica para outro fim de semana', duration: 2400, position: 'top' })
    await toast.present()
  } catch {
    const toast = await toastController.create({ message: 'Não foi possível tirar o roteiro.', duration: 2400, color: 'danger', position: 'top' })
    await toast.present()
  }
}

onMounted(async () => {
  try {
    roteiro.value = await api<Roteiro>(`/roteiros/${route.params.id}/`)
    roteiros.marcarVisto(roteiro.value.id)
  } catch {
    roteiro.value = null
  } finally {
    carregando.value = false
  }
})
</script>

<style scoped>
.abertura {
  margin: 10px 20px 8px;
  line-height: 1.5;
  color: var(--chasque-tinta-suave);
}

/* a trilha: uma linha de estrada de chão ligando os marcos do dia */
.trilha {
  position: relative;
  margin: 12px 16px 0;
  padding: 0;
  list-style: none;
}

.trilha::before {
  content: '';
  position: absolute;
  left: 21px;
  top: 30px;
  bottom: 42px;
  width: 3px;
  border-radius: 3px;
  background: repeating-linear-gradient(to bottom, var(--chasque-ocre) 0 9px, transparent 9px 16px);
  transform-origin: top;
  animation: estrada 0.9s 0.15s ease-out both;
}

.parada {
  position: relative;
  display: grid;
  grid-template-columns: 45px 1fr;
  column-gap: 12px;
  padding-bottom: 6px;
  animation: parada 0.45s ease-out both;
  animation-delay: calc(0.25s + var(--i) * 0.18s);
}

.parada__caminho {
  grid-column: 2;
  margin: 4px 0 8px;
  font-size: 0.8rem;
  color: var(--chasque-tinta-suave);
}

.parada__marco {
  grid-column: 1;
  position: relative;
  z-index: 1;
  width: 45px;
  height: 45px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 21px;
  color: var(--chasque-sobre-ocre);
  background: var(--chasque-ocre);
  box-shadow: 0 0 0 5px var(--chasque-fundo);
}

.parada__corpo {
  grid-column: 2;
  min-width: 0;
}

.parada__momento {
  margin: 2px 0 6px;
  font-family: var(--chasque-fonte-titulo);
  font-size: 1.05rem;
  font-weight: 650;
  color: var(--chasque-tinta);
}

.parada__cartao {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 12px 12px 14px;
  color: inherit;
  text-decoration: none;
  transition: transform 0.15s ease;
}

a.parada__cartao:active {
  transform: scale(0.98);
}

.parada__origem {
  flex: none;
  align-self: flex-start;
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  background: var(--chasque-neblina);
  color: var(--chasque-tinta-suave);
}

.acoes {
  margin: 22px 16px 0;
  display: grid;
  gap: 6px;
}

.acoes .botao--texto {
  color: var(--chasque-tinta-suave);
}

.nota {
  margin: 10px 20px 28px;
  font-size: 0.8rem;
  line-height: 1.45;
  color: var(--chasque-tinta-suave);
  text-align: center;
}

@keyframes estrada {
  from {
    transform: scaleY(0);
  }
}

@keyframes parada {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
}

@media (max-width: 359px) {
  .parada__origem {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .trilha::before,
  .parada {
    animation: none;
  }
}
</style>
