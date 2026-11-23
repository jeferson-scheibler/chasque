<template>
  <ion-page>
    <faixa :titulo="pessoa?.nome ?? 'Pessoa'" :subtitulo="subtitulo" voltar="/abas/conta/pessoas" />

    <ion-content class="vale">
      <!-- busca reversa: o que esta pessoa aprovou, e em que ocasião -->
      <div class="filtros">
        <div class="ocasioes" role="radiogroup" aria-label="Ocasião">
          <button
            v-for="o in OCASIOES"
            :key="o.valor"
            type="button"
            role="radio"
            :aria-checked="ocasiao === o.valor"
            :class="{ ativa: ocasiao === o.valor }"
            @click="ocasiao = o.valor"
          >
            {{ o.rotulo }}
          </button>
        </div>
        <label class="boas">
          <ion-toggle v-model="soAsBoas" aria-label="Só as visitas de 4 e 5 sóis" />
          <span>Só as que {{ primeiroNome }} mais gostou</span>
        </label>
      </div>

      <div v-if="carregando && !visitas.length" class="ion-padding ion-text-center"><ion-spinner name="crescent" /></div>

      <p v-else-if="naoSegue" class="aviso">Você não segue mais esta pessoa.</p>

      <p v-else-if="!visitas.length" class="aviso">
        {{ ocasiao || soAsBoas ? 'Nenhuma visita com esse filtro.' : `${primeiroNome} ainda não compartilhou visitas.` }}
      </p>

      <ul v-else class="linhas">
        <li v-for="v in visitas" :key="v.id">
          <button type="button" class="linha visita" @click="acoes(v)">
            <span class="linha__icone"><ion-icon :icon="iconeDaCategoria(v.lugar.categoria)" aria-hidden="true" /></span>
            <span class="linha__texto">
              <span class="visita__topo">
                <span class="linha__titulo">{{ v.lugar.nome }}</span>
                <sois :model-value="v.nota" somente-leitura />
              </span>
              <span class="linha__meta">{{ meta(v) }}</span>
              <span v-if="v.motivo" class="visita__fala">"{{ v.motivo }}"</span>
              <span v-if="v.tags.length" class="visita__motivos">
                <span v-for="slug in v.tags.slice(0, 3)" :key="slug">{{ motivos.nome(slug) }}</span>
              </span>
            </span>
          </button>
        </li>
      </ul>

      <ion-infinite-scroll :disabled="!temMais" @ion-infinite="carregarMais($event)">
        <ion-infinite-scroll-content />
      </ion-infinite-scroll>

      <button v-if="ligacao" type="button" class="botao botao--perigo deixar" @click="confirmarDeixar">
        Deixar de seguir
      </button>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import {
  actionSheetController, alertController, IonContent, IonIcon, IonInfiniteScroll, IonInfiniteScrollContent,
  IonPage, IonSpinner, IonToggle, onIonViewWillEnter, type InfiniteScrollCustomEvent,
} from '@ionic/vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Faixa from '@/components/Faixa.vue'
import Sois from '@/components/Sois.vue'
import { iconeDaCategoria } from '@/categorias'
import { api, ErroApi } from '@/services/api'
import { useMotivos } from '@/stores/motivos'
import type { Pagina, Pessoa, Registro } from '@/types'

type VisitaDela = Omit<Registro, 'privado' | 'criado_em'>
type Resposta = Pagina<VisitaDela> & { pessoa: Pessoa }

const OCASIOES = [
  { valor: '', rotulo: 'Todas' },
  { valor: 'sozinho', rotulo: 'Sozinho' },
  { valor: 'casal', rotulo: 'Casal' },
  { valor: 'familia', rotulo: 'Família' },
  { valor: 'amigos', rotulo: 'Amigos' },
  { valor: 'trabalho', rotulo: 'Trabalho' },
]
const COM_QUEM: Record<string, string> = {
  sozinho: 'sozinho', casal: 'em casal', familia: 'com a família', amigos: 'com amigos', trabalho: 'a trabalho',
}

const route = useRoute()
const router = useRouter()
const motivos = useMotivos()

const pessoa = ref<Pessoa | null>(null)
const visitas = ref<VisitaDela[]>([])
const total = ref(0)
const pagina = ref(1)
const temMais = ref(false)
const carregando = ref(false)
const naoSegue = ref(false)
const ocasiao = ref('')
const soAsBoas = ref(false)
const ligacao = ref<number | null>(null)

const idPessoa = computed(() => Number(route.params.id))
const primeiroNome = computed(() => pessoa.value?.nome.split(' ')[0] ?? 'Esta pessoa')
const subtitulo = computed(() =>
  total.value ? `${total.value} ${total.value === 1 ? 'visita compartilhada' : 'visitas compartilhadas'}` : 'Pessoa de confiança',
)
const formatoData = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short', year: 'numeric' })

function meta(v: VisitaDela) {
  const quando = formatoData.format(new Date(`${v.visitado_em}T12:00:00`)).replace('.', '')
  return [v.lugar.cidade, `${quando}, ${COM_QUEM[v.ocasiao]}`].filter(Boolean).join('. ')
}

async function buscar(n: number) {
  const p = new URLSearchParams({ page: String(n) })
  if (ocasiao.value) p.set('ocasiao', ocasiao.value)
  if (soAsBoas.value) p.set('boas', '1')
  const r = await api<Resposta>(`/pessoas/${idPessoa.value}/visitas/?${p}`)
  pessoa.value = r.pessoa
  temMais.value = r.next !== null
  pagina.value = n
  total.value = !ocasiao.value && !soAsBoas.value ? r.count : total.value
  return r.results
}

async function carregar() {
  carregando.value = true
  naoSegue.value = false
  try {
    await motivos.carregar()
    visitas.value = await buscar(1)
  } catch (e) {
    if (e instanceof ErroApi && e.status === 404) {
      naoSegue.value = true
      visitas.value = []
    }
  } finally {
    carregando.value = false
  }
}

async function carregarMais(evento: InfiniteScrollCustomEvent) {
  try {
    visitas.value.push(...(await buscar(pagina.value + 1)))
  } finally {
    await evento.target.complete()
  }
}

async function acharLigacao() {
  const r = await api<{ seguindo: { id: number; pessoa: Pessoa }[] }>('/pessoas/')
  ligacao.value = r.seguindo.find((s) => s.pessoa.id === idPessoa.value)?.id ?? null
}

async function acoes(v: VisitaDela) {
  const folha = await actionSheetController.create({
    header: v.lugar.nome,
    subHeader: meta(v),
    buttons: [
      {
        text: 'Como chegar',
        handler: () => {
          window.open(`https://www.google.com/maps/dir/?api=1&destination=${v.lugar.lat},${v.lugar.lng}`, '_blank', 'noopener')
        },
      },
      { text: 'Já fui, registrar visita', handler: () => { void router.push({ path: '/abas/lugares/visita/nova', query: { lugar: v.lugar.id } }) } },
      { text: 'Fechar', role: 'cancel' },
    ],
  })
  await folha.present()
}

async function confirmarDeixar() {
  const alerta = await alertController.create({
    header: `Deixar de seguir ${primeiroNome.value}?`,
    message: 'Você para de ver as visitas compartilhadas. Para voltar, é preciso um convite de novo.',
    buttons: [
      { text: 'Cancelar', role: 'cancel' },
      {
        text: 'Deixar de seguir',
        role: 'destructive',
        handler: () => {
          void api(`/confiancas/${ligacao.value}/`, { method: 'DELETE' }).then(() => router.replace('/abas/conta/pessoas'))
        },
      },
    ],
  })
  await alerta.present()
}

watch([ocasiao, soAsBoas], () => { void carregar() })

onIonViewWillEnter(() => {
  void carregar()
  void acharLigacao()
})
</script>

<style scoped>
.filtros {
  padding: 0 16px 8px;
}

.ocasioes {
  display: flex;
  gap: 8px;
  margin: 0 -16px;
  padding: 0 16px 4px;
  overflow-x: auto;
  scrollbar-width: none;
}

.ocasioes::-webkit-scrollbar {
  display: none;
}

.ocasioes button {
  flex: none;
  height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  border: 0;
  background: var(--chasque-neblina);
  color: var(--chasque-tinta);
  font: inherit;
  font-size: 0.9rem;
  font-weight: 500;
}

.ocasioes button.ativa {
  background: var(--chasque-faixa);
  color: var(--chasque-faixa-texto);
}

@media (prefers-color-scheme: dark) {
  .ocasioes button.ativa {
    background: var(--chasque-faixa-texto);
    color: var(--chasque-faixa);
  }
}

.boas {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  font-size: 0.9rem;
  color: var(--chasque-tinta);
}

.boas ion-toggle {
  --track-background-checked: var(--chasque-ocre);
}

.aviso {
  margin: 28px 24px;
  text-align: center;
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

.visita__fala {
  display: block;
  margin-top: 6px;
  font-size: 0.9rem;
  font-style: italic;
  color: var(--chasque-tinta);
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

.deixar {
  margin: 24px auto 0;
  width: auto;
  padding: 0 18px;
}
</style>
