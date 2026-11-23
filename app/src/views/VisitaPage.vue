<template>
  <ion-page>
    <faixa :titulo="titulo" :subtitulo="subtitulo" voltar="/abas/lugares" />

    <ion-content class="vale">
      <div v-if="carregando" class="ion-padding ion-text-center"><ion-spinner name="crescent" /></div>

      <form v-else id="form-visita" class="visita" novalidate @submit.prevent="salvar">
        <!-- Onde -->
        <section class="passo">
          <h2 class="passo__titulo">Onde você foi?</h2>
          <div v-if="lugar" class="lugar-escolhido">
            <span class="linha__icone"><ion-icon :icon="iconeDaCategoria(lugar.categoria)" aria-hidden="true" /></span>
            <span class="linha__texto">
              <span class="linha__titulo">{{ lugar.nome }}</span>
              <span class="linha__meta">{{ resumoDoLugar(lugar) || 'Lugar' }}</span>
            </span>
            <button v-if="!editando" type="button" class="trocar" @click="lugar = null">Trocar</button>
          </div>
          <div v-else class="passo__busca">
            <busca-lugar @escolher="escolherLugar" />
          </div>
        </section>

        <!-- Como foi -->
        <section class="passo">
          <h2 class="passo__titulo">Como foi?</h2>
          <sois v-model="nota" />
        </section>

        <!-- Por quê -->
        <section class="passo">
          <h2 class="passo__titulo">{{ nota && nota <= 2 ? 'O que não funcionou?' : 'O que fez diferença?' }}</h2>
          <p class="passo__apoio">É isso que ensina ao Chasque do que você gosta. Marque quantos quiser.</p>
          <template v-if="sugeridos.length">
            <h3 class="grupo">Deste lugar</h3>
            <escolhas v-model="tags" :opcoes="sugeridos" multipla rotulo="Motivos sugeridos para este lugar" />
          </template>
          <template v-for="grupo in gruposSemSugeridos" :key="grupo.nome">
            <h3 class="grupo">{{ grupo.nome }}</h3>
            <escolhas v-model="tags" :opcoes="grupo.opcoes" multipla :rotulo="grupo.nome" />
          </template>
        </section>

        <!-- Com quem -->
        <section class="passo">
          <h2 class="passo__titulo">Com quem?</h2>
          <escolhas v-model="ocasiao" :opcoes="OCASIOES" rotulo="Com quem você foi" />
        </section>

        <!-- Quando -->
        <section class="passo">
          <h2 class="passo__titulo">Quando?</h2>
          <escolhas v-model="quandoEscolha" :opcoes="QUANDO" rotulo="Quando foi a visita" />
          <input
            v-if="quandoEscolha === 'outro'"
            v-model="data"
            class="data"
            type="date"
            :max="hoje"
            aria-label="Data da visita"
          />
        </section>

        <!-- Quem pode ver -->
        <section class="passo">
          <h2 class="passo__titulo">Quem pode ver?</h2>
          <escolhas v-model="visibilidade" :opcoes="VISIBILIDADE" rotulo="Quem pode ver esta visita" />
          <p class="passo__apoio passo__apoio--depois">
            {{ visibilidade === 'confianca'
              ? 'Suas pessoas de confiança veem esta visita: o lugar, a nota, os motivos e o que você escreveu.'
              : 'Só você vê esta visita.' }}
          </p>
        </section>

        <!-- Conte mais -->
        <section class="passo">
          <h2 class="passo__titulo">Quer contar mais?</h2>
          <textarea
            v-model="motivo"
            class="papel"
            rows="3"
            maxlength="500"
            placeholder="A cuca de banana, a vista da janela, o atendimento da dona Ilse..."
            aria-label="Conte mais sobre a visita"
          />
        </section>

        <button v-if="editando" type="button" class="botao botao--perigo apagar" @click="confirmarExclusao">
          <ion-icon :icon="trashOutline" aria-hidden="true" />Apagar visita
        </button>
      </form>
    </ion-content>

    <ion-footer v-if="!carregando" class="rodape">
      <p v-if="erro" class="mensagem-erro" role="alert">{{ erro }}</p>
      <button type="submit" form="form-visita" class="botao botao--sol" :disabled="salvando">
        {{ salvando ? 'Salvando...' : editando ? 'Salvar alterações' : 'Registrar visita' }}
      </button>
    </ion-footer>

    <!-- visita nova: o chasque aprova antes de voltar para a lista -->
    <div v-if="comemorando" class="aprovado" role="status">
      <div class="aprovado__cartao">
        <mascote pose="aprovando" class="aprovado__chasque" />
        <p class="aprovado__titulo">Visita registrada</p>
        <p class="aprovado__texto">{{ lugar?.nome }} já está ensinando o seu gosto ao Chasque.</p>
      </div>
    </div>
  </ion-page>
</template>

<script setup lang="ts">
import {
  alertController, IonContent, IonFooter, IonIcon, IonPage, IonSpinner, toastController,
} from '@ionic/vue'
import {
  briefcaseOutline, heartOutline, homeOutline, lockClosedOutline, peopleOutline, personOutline, trashOutline,
} from 'ionicons/icons'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BuscaLugar from '@/components/BuscaLugar.vue'
import Escolhas, { type Opcao } from '@/components/Escolhas.vue'
import Faixa from '@/components/Faixa.vue'
import Mascote from '@/components/Mascote.vue'
import Sois from '@/components/Sois.vue'
import { iconeDaCategoria } from '@/categorias'
import { api, ErroApi, mensagemDe } from '@/services/api'
import { useMotivos } from '@/stores/motivos'
import { resumoDoLugar, type Lugar, type Registro, type Salvo } from '@/types'

const OCASIOES: Opcao[] = [
  { valor: 'sozinho', rotulo: 'Sozinho', icone: personOutline },
  { valor: 'casal', rotulo: 'Casal', icone: heartOutline },
  { valor: 'familia', rotulo: 'Família', icone: homeOutline },
  { valor: 'amigos', rotulo: 'Amigos', icone: peopleOutline },
  { valor: 'trabalho', rotulo: 'Trabalho', icone: briefcaseOutline },
]
const VISIBILIDADE: Opcao[] = [
  { valor: 'privado', rotulo: 'Só eu', icone: lockClosedOutline },
  { valor: 'confianca', rotulo: 'Pessoas de confiança', icone: peopleOutline },
]
const CHAVE_VISIBILIDADE = 'chasque-visibilidade'
const QUANDO: Opcao[] = [
  { valor: 'hoje', rotulo: 'Hoje' },
  { valor: 'ontem', rotulo: 'Ontem' },
  { valor: 'outro', rotulo: 'Outro dia' },
]

const route = useRoute()
const router = useRouter()
const motivos = useMotivos()

const idRegistro = computed(() => (route.params.id ? Number(route.params.id) : null))
const editando = computed(() => idRegistro.value !== null)

const carregando = ref(true)
const salvando = ref(false)
const erro = ref('')

const lugar = ref<Lugar | null>(null)
const comemorando = ref(false)
const nota = ref(0)
const tags = ref<string[]>([])
const ocasiao = ref<string | null>(null)
const motivo = ref('')
const quandoEscolha = ref<string>('hoje')
// Privada por padrão; depois lembra a última escolha neste aparelho.
const visibilidade = ref<string>(lerVisibilidade())

function lerVisibilidade() {
  try {
    return localStorage.getItem(CHAVE_VISIBILIDADE) === 'confianca' ? 'confianca' : 'privado'
  } catch {
    return 'privado'
  }
}
const data = ref('')

function isoLocal(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const hoje = isoLocal(new Date())
const ontem = isoLocal(new Date(Date.now() - 86_400_000))

const dataEscolhida = computed(() =>
  quandoEscolha.value === 'hoje' ? hoje : quandoEscolha.value === 'ontem' ? ontem : data.value,
)

const titulo = computed(() => (editando.value && lugar.value ? lugar.value.nome : 'Registrar visita'))
const subtitulo = computed(() => (editando.value ? 'Sua visita' : lugar.value ? lugar.value.nome : 'Três toques e pronto'))

// Os motivos que o OSM já sugere para o lugar aparecem primeiro, num grupo à parte.
// Primeiro o que outras pessoas confirmaram (comunidade), depois o que vem do OpenStreetMap.
const slugsDoLugar = computed(() => [
  ...new Set([...(lugar.value?.motivos_comunidade ?? []).map((m) => m.slug), ...(lugar.value?.tags ?? [])]),
])
const sugeridos = computed<Opcao[]>(() => slugsDoLugar.value.map((slug) => ({ valor: slug, rotulo: motivos.nome(slug) })))
const gruposSemSugeridos = computed(() => {
  const jaMostrados = new Set(slugsDoLugar.value)
  return motivos.grupos
    .map((g) => ({
      nome: g.nome,
      opcoes: g.motivos.filter((m) => !jaMostrados.has(m.slug)).map((m) => ({ valor: m.slug, rotulo: m.nome })),
    }))
    .filter((g) => g.opcoes.length)
})

watch(quandoEscolha, (valor) => {
  if (valor === 'outro' && !data.value) data.value = ontem
})

function escolherLugar(escolhido: Lugar) {
  lugar.value = escolhido
}

async function carregar() {
  carregando.value = true
  try {
    await motivos.carregar()
    if (editando.value) {
      const r = await api<Registro>(`/registros/${idRegistro.value}/`)
      lugar.value = r.lugar
      nota.value = r.nota
      tags.value = [...r.tags]
      ocasiao.value = r.ocasiao
      motivo.value = r.motivo
      visibilidade.value = r.privado ? 'privado' : 'confianca'
      if (r.visitado_em === hoje) quandoEscolha.value = 'hoje'
      else if (r.visitado_em === ontem) quandoEscolha.value = 'ontem'
      else {
        quandoEscolha.value = 'outro'
        data.value = r.visitado_em
      }
    } else if (typeof route.query.salvo === 'string') {
      // Vindo de um link salvo: o lugar e a anotação já vêm preenchidos.
      const salvo = await api<Salvo>(`/salvos/${route.query.salvo}/`)
      lugar.value = salvo.lugar
      motivo.value = salvo.texto.slice(0, 500)
    } else if (typeof route.query.lugar === 'string') {
      lugar.value = await api<Lugar>(`/lugares/${route.query.lugar}/`)
    }
  } catch {
    erro.value = 'Não foi possível carregar. Tente de novo.'
  } finally {
    carregando.value = false
  }
}

function validar(): string {
  if (!lugar.value) return 'Escolha o lugar onde você foi.'
  if (!nota.value) return 'Toque nos sóis para dizer como foi.'
  if (!tags.value.length && !motivo.value.trim()) return 'Marque pelo menos um motivo ou conte um pouco.'
  if (!ocasiao.value) return 'Diga com quem você foi.'
  if (!dataEscolhida.value) return 'Escolha a data da visita.'
  return ''
}

async function avisar(mensagem: string, cor?: string) {
  const toast = await toastController.create({ message: mensagem, duration: 2400, color: cor, position: 'top' })
  await toast.present()
}

async function salvar() {
  erro.value = validar()
  if (erro.value) return
  salvando.value = true
  const corpo = {
    lugar_id: lugar.value!.id,
    nota: nota.value,
    tags: tags.value,
    ocasiao: ocasiao.value,
    motivo: motivo.value.trim(),
    visitado_em: dataEscolhida.value,
    privado: visibilidade.value !== 'confianca',
  }
  try {
    localStorage.setItem(CHAVE_VISIBILIDADE, visibilidade.value)
  } catch {
    // sem armazenamento: só não lembra a escolha
  }
  try {
    if (editando.value) {
      await api(`/registros/${idRegistro.value}/`, { method: 'PATCH', json: corpo })
      await avisar('Visita atualizada')
    } else {
      await api('/registros/', { method: 'POST', json: corpo })
      comemorando.value = true
      const reduzido = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      await new Promise((r) => setTimeout(r, reduzido ? 900 : 1500))
    }
    await router.replace({ path: '/abas/lugares', query: { aba: 'visitados' } })
  } catch (e) {
    erro.value = e instanceof ErroApi ? mensagemDe(e.dados) ?? e.message : 'Sem conexão com o servidor.'
  } finally {
    salvando.value = false
    comemorando.value = false
  }
}

async function confirmarExclusao() {
  const alerta = await alertController.create({
    header: 'Apagar esta visita?',
    message: 'O que ela ensinou sobre o seu gosto também sai do perfil.',
    buttons: [
      { text: 'Cancelar', role: 'cancel' },
      { text: 'Apagar', role: 'destructive', handler: () => { void apagar() } },
    ],
  })
  await alerta.present()
}

async function apagar() {
  try {
    await api(`/registros/${idRegistro.value}/`, { method: 'DELETE' })
    await router.replace({ path: '/abas/lugares', query: { aba: 'visitados' } })
    await avisar('Visita apagada')
  } catch {
    await avisar('Não foi possível apagar.', 'danger')
  }
}

onMounted(carregar)
</script>

<style scoped>
.aprovado {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: grid;
  place-items: center;
  padding: 24px;
  background: color-mix(in srgb, var(--chasque-faixa) 55%, transparent);
  backdrop-filter: blur(3px);
  animation: aparecer 0.25s ease-out both;
}

.aprovado__cartao {
  width: min(300px, 100%);
  padding: 26px 24px 22px;
  border-radius: 28px;
  background: var(--colina-perto);
  text-align: center;
  box-shadow: 0 18px 50px rgb(15 21 36 / 0.35);
  animation: subir 0.45s cubic-bezier(0.2, 0.9, 0.3, 1.25) both;
}

.aprovado__chasque {
  height: 140px;
  width: auto;
  margin: 0 auto 12px;
}

.aprovado__titulo {
  margin: 0 0 6px;
  font-family: var(--chasque-fonte-titulo);
  font-size: 1.35rem;
  font-weight: 650;
  color: var(--chasque-tinta);
}

.aprovado__texto {
  margin: 0;
  line-height: 1.45;
  color: var(--chasque-tinta-suave);
}

@keyframes aparecer {
  from {
    opacity: 0;
  }
}

@keyframes subir {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.94);
  }
}

@media (prefers-reduced-motion: reduce) {
  .aprovado,
  .aprovado__cartao {
    animation: none;
  }
}

.visita {
  padding-bottom: 24px;
}

.passo {
  padding: 4px 20px 22px;
}

.passo + .passo {
  border-top: 1px solid var(--chasque-neblina);
  padding-top: 20px;
}

.passo__titulo {
  margin: 0 0 12px;
  font-size: 1.25rem;
  font-weight: 650;
  color: var(--chasque-tinta);
}

.passo__apoio {
  margin: -6px 0 12px;
  font-size: 0.875rem;
  color: var(--chasque-tinta-suave);
}

.passo__apoio--depois {
  margin: 10px 0 0;
}

.passo__busca {
  margin: 0 -20px;
}

.grupo {
  margin: 16px 0 8px;
  font-family: var(--ion-font-family);
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--chasque-tinta-suave);
}

.lugar-escolhido {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 12px 12px 14px;
  border-radius: 18px;
  background: var(--chasque-papel);
  border: 1px solid var(--chasque-neblina);
}

.trocar {
  flex: none;
  border: 0;
  background: transparent;
  color: var(--chasque-tinta);
  font: inherit;
  font-weight: 600;
  text-decoration: underline;
  text-decoration-color: var(--chasque-ocre);
  text-underline-offset: 4px;
  padding: 8px;
}

.data {
  display: block;
  margin-top: 12px;
  height: 48px;
  padding: 0 14px;
  border-radius: 14px;
  border: 1.5px solid var(--chasque-neblina);
  background: var(--chasque-papel);
  color: var(--chasque-tinta);
  font: inherit;
  font-size: 1rem;
}

/* papel pautado, como a anotação dos salvos */
.papel {
  display: block;
  width: 100%;
  padding: 6px 16px 8px;
  border: 1px solid var(--chasque-neblina);
  border-radius: 18px;
  background-color: var(--chasque-papel);
  background-image: repeating-linear-gradient(
    to bottom,
    transparent 0,
    transparent 31px,
    var(--chasque-neblina) 31px,
    var(--chasque-neblina) 32px
  );
  background-attachment: local;
  background-position: 0 6px;
  font: inherit;
  font-size: 1rem;
  line-height: 32px;
  color: var(--chasque-tinta);
  resize: vertical;
  outline: none;
}

.papel:focus {
  border-color: var(--chasque-faixa);
}

.apagar {
  margin: 4px auto 0;
  width: auto;
  padding: 0 18px;
}

.rodape {
  padding: 12px 20px calc(12px + var(--ion-safe-area-bottom, 0px) * 0);
  background: var(--chasque-fundo);
  border-top: 1px solid var(--chasque-neblina);
}

.rodape .mensagem-erro {
  margin-bottom: 10px;
}

.rodape::before {
  display: none;
}
</style>
