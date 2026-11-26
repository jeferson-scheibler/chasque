<template>
  <ion-page>
    <faixa titulo="Sugestões" subtitulo="Pelo seu gosto, não pela média" />

    <ion-content class="vale">
      <ion-refresher slot="fixed" @ion-refresh="atualizar($event)">
        <ion-refresher-content />
      </ion-refresher>

      <!-- Onde e com quem -->
      <div v-if="temGosto" class="filtros">
        <div class="pilulas">
        <button type="button" class="onde" :aria-expanded="mostrarOnde" @click="mostrarOnde = !mostrarOnde">
          <ion-icon :icon="origem?.tipo === 'localizacao' ? navigateOutline : locationOutline" aria-hidden="true" />
          <span>{{ origem ? origem.nome : 'Escolher onde' }}</span>
        </button>
        <button type="button" class="onde quando" :class="{ 'quando--ativo': quando }" :aria-expanded="mostrarQuando" @click="mostrarQuando = !mostrarQuando">
          <ion-icon :icon="calendarOutline" aria-hidden="true" />
          <span>{{ rotuloQuando }}</span>
        </button>
        </div>
        <div v-if="mostrarOnde" class="onde__painel">
          <button type="button" class="botao botao--leve" :disabled="localizando" @click="usarLocalizacao">
            <ion-icon :icon="navigateOutline" aria-hidden="true" />
            {{ localizando ? 'Localizando...' : 'Usar minha localização' }}
          </button>
          <escolher-cidade v-model="cidadeId" :cidades="cidades" />
        </div>
        <div v-if="mostrarQuando" class="onde__painel quando__painel">
          <div class="quando__rapido" role="radiogroup" aria-label="Dia">
            <button v-for="d in DIAS_RAPIDOS" :key="d.rotulo" type="button" role="radio"
                    :aria-checked="quando === d.valor()" :class="{ ativa: quando === d.valor() }" @click="escolherDia(d.valor())">
              {{ d.rotulo }}
            </button>
          </div>
          <label class="quando__campo">
            <span>Outro dia</span>
            <input v-model="quando" type="date" :min="hoje()" aria-label="Dia da visita" />
          </label>
          <label v-if="quando" class="quando__campo">
            <span>Horário (opcional)</span>
            <input v-model="hora" type="time" aria-label="Horário da visita" />
          </label>
          <p class="quando__apoio">
            Lugares que o mapa mostra fechados nesse dia saem da lista. Os sem horário continuam, com aviso.
          </p>
          <button v-if="quando" type="button" class="botao botao--texto quando__limpar" @click="limparQuando">Qualquer dia</button>
        </div>
        <div class="ocasioes tipos" role="radiogroup" aria-label="Que tipo de lugar">
          <button
            v-for="o in TIPOS"
            :key="o.valor"
            type="button"
            role="radio"
            :aria-checked="tipo === o.valor"
            :class="{ ativa: tipo === o.valor }"
            @click="tipo = o.valor"
          >
            {{ o.rotulo }}
          </button>
        </div>
        <div class="ocasioes" role="radiogroup" aria-label="Com quem você vai">
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
      </div>

      <div v-if="carregando && !carregou" class="esqueleto" aria-label="Carregando">
        <ion-skeleton-text :animated="true" class="esqueleto__destaque" />
        <ion-skeleton-text v-for="n in 3" :key="n" :animated="true" class="esqueleto__linha" />
      </div>

      <!-- Primeiros gostos: dá sugestão antes da primeira visita -->
      <section v-else-if="!temGosto || editandoGostos" class="gostos">
        <h2>{{ editandoGostos ? 'Seus gostos' : 'Do que você gosta?' }}</h2>
        <p class="texto-apoio">
          Marque o que faz um lugar valer a pena para você. Depois, cada visita que você registra afina as sugestões.
        </p>
        <template v-for="grupo in gruposDeMotivos" :key="grupo.nome">
          <h3 class="grupo">{{ grupo.nome }}</h3>
          <escolhas v-model="gostos" :opcoes="grupo.opcoes" multipla :rotulo="grupo.nome" />
        </template>
        <p v-if="erro" class="mensagem-erro" role="alert">{{ erro }}</p>
        <button type="button" class="botao botao--sol" :disabled="salvandoGostos" @click="salvarGostos">
          {{ salvandoGostos ? 'Salvando...' : gostos.length ? `Ver sugestões (${gostos.length})` : 'Ver sugestões' }}
        </button>
        <button v-if="editandoGostos" type="button" class="botao botao--texto" @click="editandoGostos = false">Cancelar</button>
      </section>

      <vazio
        v-else-if="!origem"
        pose="espiando"
        titulo="Onde você quer procurar?"
        texto="Use a sua localização ou escolha uma cidade do RS."
      >
        <button type="button" class="botao botao--sol botao--compacto" @click="usarLocalizacao">
          <ion-icon :icon="navigateOutline" aria-hidden="true" />Usar minha localização
        </button>
      </vazio>

      <vazio
        v-else-if="!resultados.length"
        pose="duvida"
        :titulo="quando ? 'Nada aberto nesse dia por perto' : 'Nada por perto combina ainda'"
        :texto="quando
          ? 'Os lugares com horário no mapa estão fechados nesse dia. Tente outro dia, outra cidade ou tire o horário.'
          : 'Tente outra cidade ou outra ocasião. Cada visita que você registra ajuda o Chasque a achar mais lugares.'"
      >
        <button v-if="quando" type="button" class="botao botao--leve botao--compacto" @click="limparQuando">Ver qualquer dia</button>
      </vazio>

      <template v-else>
        <!-- A melhor combinação: o único destaque da tela -->
        <article class="destaque">
          <p class="destaque__rotulo">{{ tipo && !primeira.combina.length ? 'A mais perto de você' : ocasiao === 'grupo' ? 'A que mais serve para o grupo' : 'A que mais combina com você' }}</p>
          <h2>{{ primeira.lugar.nome }}</h2>
          <p class="destaque__meta">{{ metaDo(primeira) }}</p>
          <p v-if="avisoHorario(primeira)" class="horario" :class="`horario--${primeira.horario?.estado}`">
            <ion-icon :icon="timeOutline" aria-hidden="true" />{{ avisoHorario(primeira) }}
          </p>
          <p v-if="avisoGrupo(primeira)" class="horario">
            <ion-icon :icon="peopleCircleOutline" aria-hidden="true" />{{ avisoGrupo(primeira) }}
          </p>
          <p class="destaque__combina">
            <span v-for="slug in primeira.combina" :key="slug">
              {{ motivos.nome(slug) }}
              <template v-if="primeira.comunidade[slug]">
                <ion-icon :icon="peopleOutline" aria-hidden="true" />{{ primeira.comunidade[slug] }}
              </template>
            </span>
          </p>
          <p v-if="pessoas(primeira)" class="destaque__pessoas">{{ textoPessoas(primeira) }}</p>
          <div class="destaque__acoes">
            <a class="botao botao--sol botao--compacto" :href="rota(primeira)" target="_blank" rel="noopener noreferrer">
              <ion-icon :icon="navigateOutline" aria-hidden="true" />Como chegar
            </a>
            <a v-if="primeira.lugar.telefone && primeira.horario?.estado !== 'aberto'" class="destaque__fui" :href="`tel:${primeira.lugar.telefone}`">
              Ligar
            </a>
            <router-link class="destaque__fui" :to="{ path: '/abas/lugares/visita/nova', query: { lugar: primeira.lugar.id } }">
              Já fui
            </router-link>
          </div>
        </article>

        <h2 v-if="demais.length" class="secao-titulo">Também combinam</h2>
        <ul class="linhas">
          <li v-for="s in demais" :key="s.lugar.id">
            <button type="button" class="linha" @click="acoes(s)">
              <span class="linha__icone"><ion-icon :icon="iconeDaCategoria(s.lugar.categoria)" aria-hidden="true" /></span>
              <span class="linha__texto">
                <span class="linha__titulo">{{ s.lugar.nome }}</span>
                <span class="linha__meta">{{ metaDo(s) }}</span>
                <span v-if="avisoHorario(s)" class="horario" :class="`horario--${s.horario?.estado}`">
                  <ion-icon :icon="timeOutline" aria-hidden="true" />{{ avisoHorario(s) }}
                </span>
                <span v-if="avisoGrupo(s)" class="horario">
                  <ion-icon :icon="peopleCircleOutline" aria-hidden="true" />{{ avisoGrupo(s) }}
                </span>
                <span v-if="s.combina.length" class="combina">Combina com {{ listaDeMotivos(s.combina) }}</span>
                <span v-if="pessoas(s)" class="pessoas">
                  <ion-icon :icon="peopleOutline" aria-hidden="true" />{{ textoPessoas(s) }}
                </span>
              </span>
              <span v-if="s.salvo" class="salvo">Salvo</span>
            </button>
          </li>
        </ul>

        <p class="rodape-sugestoes">
          <button type="button" class="ajustar" @click="abrirGostos">Ajustar meus gostos</button>
        </p>
      </template>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import {
  actionSheetController, IonContent, IonIcon, IonPage, IonRefresher, IonRefresherContent, IonSkeletonText,
  onIonViewWillEnter, type RefresherCustomEvent,
} from '@ionic/vue'
import { calendarOutline, locationOutline, navigateOutline, peopleCircleOutline, peopleOutline, timeOutline } from 'ionicons/icons'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import EscolherCidade from '@/components/EscolherCidade.vue'
import Escolhas from '@/components/Escolhas.vue'
import Faixa from '@/components/Faixa.vue'
import Vazio from '@/components/Vazio.vue'
import { iconeDaCategoria } from '@/categorias'
import { api, ErroApi, mensagemDe } from '@/services/api'
import { useMotivos } from '@/stores/motivos'
import { resumoDoLugar, type Cidade, type Lugar } from '@/types'

interface Sugestao {
  lugar: Lugar
  pontos: number
  combina: string[]
  /** motivo -> quantas pessoas o marcaram em visitas boas */
  comunidade: Record<string, number>
  salvo: boolean
  /** Só vem com o filtro "quando". aberto: o horário do mapa confirma; visto: alguém já foi nesse dia da semana. */
  horario: { estado: 'aberto' | 'visto' | 'sem_info'; texto: string; visitas?: number } | null
  /** Só vem na ocasião "evento ou grupo": capacidade do mapa e visitas boas registradas em grupo. */
  grupo: { capacidade: number | null; visitas: number } | null
}
interface Resposta {
  origem: { tipo: 'localizacao' | 'cidade' | 'ultima_visita'; nome: string; cidade_id: number | null } | null
  tem_gosto: boolean
  resultados: Sugestao[]
}

const OCASIOES = [
  { valor: '', rotulo: 'Qualquer' },
  { valor: 'sozinho', rotulo: 'Sozinho' },
  { valor: 'casal', rotulo: 'Casal' },
  { valor: 'familia', rotulo: 'Família' },
  { valor: 'amigos', rotulo: 'Amigos' },
  { valor: 'trabalho', rotulo: 'Trabalho' },
  { valor: 'grupo', rotulo: 'Evento ou grupo' },
]
// tipo de lugar: com um escolhido entram todos daquele tipo, e o gosto só ordena
const TIPOS = [
  { valor: '', rotulo: 'Pelo meu gosto' },
  { valor: 'bar', rotulo: 'Bar' },
  { valor: 'lanche', rotulo: 'Lanche' },
  { valor: 'restaurante', rotulo: 'Restaurante' },
  { valor: 'cafe', rotulo: 'Café e doces' },
  { valor: 'noite', rotulo: 'Vida noturna' },
  { valor: 'passeio', rotulo: 'Passeio' },
]
const CHAVE = 'chasque-sugestoes'

const router = useRouter()
const motivos = useMotivos()

const carregando = ref(false)
const carregou = ref(false)
const resultados = ref<Sugestao[]>([])
const origem = ref<Resposta['origem']>(null)
const temGosto = ref(true)
const erro = ref('')

// onde procurar: posição (só quando a pessoa toca) ou cidade; lembrado neste aparelho
const posicao = ref<{ lat: number; lng: number } | null>(null)
const cidadeId = ref<number | null>(null)
const ocasiao = ref('')
const tipo = ref('')
const mostrarOnde = ref(false)
const localizando = ref(false)
// quando: dia (AAAA-MM-DD) e hora (HH:MM) da visita; vazio = qualquer dia. Não é lembrado: data velha engana.
const quando = ref('')
const hora = ref('')
const mostrarQuando = ref(false)
const cidades = ref<Cidade[]>([])

const gostos = ref<string[]>([])
const editandoGostos = ref(false)
const salvandoGostos = ref(false)

const primeira = computed(() => resultados.value[0])
const demais = computed(() => resultados.value.slice(1))
const gruposDeMotivos = computed(() =>
  motivos.grupos.map((g) => ({ nome: g.nome, opcoes: g.motivos.map((m) => ({ valor: m.slug, rotulo: m.nome })) })),
)

try {
  const salvo = JSON.parse(localStorage.getItem(CHAVE) ?? '{}')
  if (typeof salvo.cidadeId === 'number') cidadeId.value = salvo.cidadeId
  if (typeof salvo.ocasiao === 'string') ocasiao.value = salvo.ocasiao
  if (typeof salvo.tipo === 'string' && TIPOS.some((o) => o.valor === salvo.tipo)) tipo.value = salvo.tipo
} catch {
  // sem armazenamento (aba anônima): começa do padrão
}

function lembrar() {
  try {
    localStorage.setItem(CHAVE, JSON.stringify({ cidadeId: cidadeId.value, ocasiao: ocasiao.value, tipo: tipo.value }))
  } catch {
    // tudo bem não lembrar
  }
}

function dataLocal(deslocar = 0) {
  const d = new Date()
  d.setDate(d.getDate() + deslocar)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const hoje = () => dataLocal()
const DIAS_RAPIDOS = [
  { rotulo: 'Hoje', valor: () => dataLocal() },
  { rotulo: 'Amanhã', valor: () => dataLocal(1) },
]

function diaDaSemana(data: string, estilo: 'long' | 'short' = 'long') {
  return new Intl.DateTimeFormat('pt-BR', { weekday: estilo }).format(new Date(`${data}T12:00:00`)).replace('.', '')
}

const rotuloQuando = computed(() => {
  if (!quando.value) return 'Quando?'
  const dia = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit' }).format(new Date(`${quando.value}T12:00:00`))
  return `${diaDaSemana(quando.value, 'short')} ${dia}${hora.value ? `, ${hora.value}` : ''}`
})

function escolherDia(valor: string) {
  quando.value = valor
}

function limparQuando() {
  quando.value = ''
  hora.value = ''
  mostrarQuando.value = false
}

/** Frase sobre o horário de um resultado (vazio se não há filtro "quando"). */
function avisoHorario(s: Sugestao) {
  const h = s.horario
  if (!h || !quando.value) return ''
  const dia = diaDaSemana(quando.value)
  if (h.estado === 'aberto') return h.texto === 'o dia todo' ? 'Aberto o dia todo nesse dia' : `Aberto nesse dia, ${h.texto}`
  if (h.estado === 'visto') {
    return h.visitas === 1 ? `Alguém já foi numa ${dia}` : `${h.visitas} pessoas já foram numa ${dia}`
  }
  return 'Sem horário no mapa: confirme antes de ir'
}

/** Frase sobre o tamanho do lugar, na ocasião "evento ou grupo". */
function avisoGrupo(s: Sugestao) {
  const g = s.grupo
  if (!g) return ''
  const partes = []
  if (g.capacidade && g.capacidade >= 20) partes.push(`Cabem umas ${g.capacidade} pessoas`)
  else if (g.capacidade) partes.push(`Pequeno: umas ${g.capacidade} pessoas`)
  if (g.visitas) partes.push(g.visitas === 1 ? 'Já recebeu um grupo e agradou' : `Já recebeu ${g.visitas} grupos e agradou`)
  return partes.join('. ')
}

function distancia(m: number | null) {
  if (m === null) return ''
  return m < 1000 ? `${Math.round(m / 10) * 10} m` : `${(m / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} km`
}

function metaDo(s: Sugestao) {
  return [resumoDoLugar(s.lugar), distancia(s.lugar.distancia_m)].filter(Boolean).join(', ')
}

function listaDeMotivos(slugs: string[]) {
  const nomes = slugs.map((s) => motivos.nome(s).toLowerCase())
  return nomes.length > 1 ? `${nomes.slice(0, -1).join(', ')} e ${nomes.at(-1)}` : nomes[0] ?? ''
}

/** Quantas pessoas confirmaram o motivo mais marcado (0 se nenhum veio da comunidade). */
function pessoas(s: Sugestao) {
  return Math.max(0, ...Object.values(s.comunidade ?? {}))
}

function textoPessoas(s: Sugestao) {
  return `Recomendado por ${pessoas(s)} pessoas que foram`
}

function rota(s: Sugestao) {
  // Só um link para o app de mapas do celular; nada do Google é guardado.
  return `https://www.google.com/maps/dir/?api=1&destination=${s.lugar.lat},${s.lugar.lng}`
}

async function carregar() {
  carregando.value = true
  erro.value = ''
  try {
    await motivos.carregar()
    const p = new URLSearchParams()
    if (posicao.value) {
      p.set('lat', String(posicao.value.lat))
      p.set('lng', String(posicao.value.lng))
    } else if (cidadeId.value) {
      p.set('cidade_id', String(cidadeId.value))
    }
    if (ocasiao.value) p.set('ocasiao', ocasiao.value)
    if (tipo.value) p.set('tipo', tipo.value)
    if (quando.value) {
      p.set('quando', quando.value)
      if (hora.value) p.set('hora', hora.value)
    }
    const r = await api<Resposta>(`/sugestoes/?${p}`)
    resultados.value = r.resultados
    origem.value = r.origem
    temGosto.value = r.tem_gosto
    if (!r.tem_gosto && !gostos.value.length) {
      gostos.value = (await api<{ tags: string[] }>('/me/preferencias/')).tags
    }
  } catch (e) {
    erro.value = e instanceof ErroApi ? e.message : 'Sem conexão com o servidor.'
  } finally {
    carregando.value = false
    carregou.value = true
  }
}

async function atualizar(evento: RefresherCustomEvent) {
  await carregar()
  await evento.target.complete()
}

function usarLocalizacao() {
  if (!('geolocation' in navigator)) return
  localizando.value = true
  // Só pede a posição quando a pessoa toca no botão; nada roda em segundo plano.
  navigator.geolocation.getCurrentPosition(
    (p) => {
      posicao.value = { lat: p.coords.latitude, lng: p.coords.longitude }
      localizando.value = false
      mostrarOnde.value = false
      void carregar()
    },
    () => {
      localizando.value = false
      mostrarOnde.value = true
    },
    { enableHighAccuracy: false, timeout: 15000, maximumAge: 300000 },
  )
}

async function abrirGostos() {
  gostos.value = (await api<{ tags: string[] }>('/me/preferencias/')).tags
  editandoGostos.value = true
}

async function salvarGostos() {
  erro.value = ''
  if (!gostos.value.length) {
    erro.value = 'Marque pelo menos um.'
    return
  }
  salvandoGostos.value = true
  try {
    await api('/me/preferencias/', { method: 'PUT', json: { tags: gostos.value } })
    editandoGostos.value = false
    await carregar()
  } catch (e) {
    erro.value = e instanceof ErroApi ? mensagemDe(e.dados) ?? e.message : 'Sem conexão com o servidor.'
  } finally {
    salvandoGostos.value = false
  }
}

async function acoes(s: Sugestao) {
  const folha = await actionSheetController.create({
    header: s.lugar.nome,
    subHeader: metaDo(s),
    buttons: [
      { text: 'Como chegar', handler: () => { window.open(rota(s), '_blank', 'noopener') } },
      ...(s.lugar.telefone ? [{ text: `Ligar para ${s.lugar.telefone}`, handler: () => { window.location.href = `tel:${s.lugar.telefone}` } }] : []),
      { text: 'Já fui, registrar visita', handler: () => { void router.push({ path: '/abas/lugares/visita/nova', query: { lugar: s.lugar.id } }) } },
      { text: 'Fechar', role: 'cancel' },
    ],
  })
  await folha.present()
}

watch(cidadeId, (novo) => {
  if (novo) {
    posicao.value = null
    mostrarOnde.value = false
    lembrar()
    void carregar()
  }
})

watch([ocasiao, tipo], () => {
  lembrar()
  void carregar()
})

watch([quando, hora], () => {
  if (!quando.value) hora.value = '' // a API só aceita horário junto com o dia
  void carregar()
})

watch(mostrarOnde, async (aberto) => {
  if (aberto && !cidades.value.length) cidades.value = await api<Cidade[]>('/cidades/')
})

onIonViewWillEnter(() => { void carregar() })
</script>

<style scoped>
.filtros {
  padding: 0 16px 6px;
}

/* onde e quando sempre na mesma linha: o texto mais longo encolhe com reticências */
.pilulas {
  display: flex;
  gap: 8px;
}

.pilulas .onde {
  flex: 0 1 auto;
  min-width: 0;
}

.onde {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
  height: 40px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1.5px solid var(--chasque-neblina);
  background: var(--chasque-papel);
  color: var(--chasque-tinta);
  font: inherit;
  font-weight: 600;
}

.onde ion-icon {
  font-size: 18px;
  color: var(--chasque-ocre);
  flex: none;
}

.onde span {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.quando--ativo {
  border-color: var(--chasque-ocre);
}

.quando__rapido {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.quando__rapido button {
  height: 36px;
  padding: 0 16px;
  border-radius: 999px;
  border: 0;
  background: var(--chasque-neblina);
  color: var(--chasque-tinta);
  font: inherit;
  font-size: 0.9rem;
  font-weight: 500;
}

.quando__rapido button.ativa {
  background: var(--chasque-faixa);
  color: var(--chasque-faixa-texto);
}

@media (prefers-color-scheme: dark) {
  .quando__rapido button.ativa {
    background: var(--chasque-faixa-texto);
    color: var(--chasque-faixa);
  }
}

.quando__campo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  font-weight: 600;
  color: var(--chasque-tinta);
}

.quando__campo input {
  height: 40px;
  padding: 0 10px;
  border-radius: 12px;
  border: 1.5px solid var(--chasque-neblina);
  background: var(--colina-perto);
  color: var(--chasque-tinta);
  font: inherit;
  color-scheme: light dark;
}

.quando__apoio {
  margin: 4px 0 0;
  font-size: 0.85rem;
  line-height: 1.4;
  color: var(--chasque-tinta-suave);
}

.quando__limpar {
  margin-top: 6px;
  height: 40px;
}

.horario {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 12px;
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--chasque-tinta);
}

.linha .horario {
  margin: 3px 0 0;
  font-size: 0.82rem;
}

.horario ion-icon {
  flex: none;
  font-size: 16px;
  color: var(--chasque-ocre);
}

.horario--sem_info {
  font-weight: 500;
  color: var(--chasque-tinta-suave);
}

.onde__painel {
  margin-top: 10px;
  padding: 14px;
  border-radius: 18px;
  background: var(--chasque-papel);
  border: 1px solid var(--chasque-neblina);
}

.onde__painel .botao {
  height: 46px;
  margin-bottom: 14px;
}

.ocasioes {
  display: flex;
  gap: 8px;
  margin: 12px -16px 0;
  padding: 0 16px 4px;
  overflow-x: auto;
  scrollbar-width: none;
}

.tipos {
  margin-top: 12px;
}

.tipos + .ocasioes {
  margin-top: 8px;
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
  transition: background-color 0.18s ease, color 0.18s ease;
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

.gostos {
  padding: 4px 20px 24px;
}

.gostos h2 {
  margin: 0 0 6px;
  font-size: 1.4rem;
  font-weight: 650;
  color: var(--chasque-tinta);
}

.gostos .botao {
  margin-top: 22px;
}

.grupo {
  margin: 16px 0 8px;
  font-family: var(--ion-font-family);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--chasque-tinta-suave);
}

/* A melhor combinação: cartão Noite com o brilho do sol nascendo no canto. */
/* a melhor combinação: sem caixa, direto no fundo da tela; só o nome grande e uma linha fina separam da lista */
.destaque {
  margin: 8px 16px 6px;
  padding: 10px 4px 24px;
  border-bottom: 1px solid var(--chasque-neblina);
}

.destaque__rotulo {
  margin: 0 0 8px;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--chasque-tinta-suave);
}

.destaque h2 {
  margin: 0;
  font-size: 2.1rem;
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.02em;
  color: var(--chasque-tinta);
}

.destaque__meta {
  margin: 10px 0 14px;
  font-size: 1.02rem;
  color: var(--chasque-tinta-suave);
}

.destaque__combina {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 20px;
}

.destaque__combina span {
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--chasque-neblina);
  color: var(--chasque-tinta);
  font-size: 0.84rem;
  font-weight: 500;
}

.destaque__combina span ion-icon {
  font-size: 13px;
  margin: 0 2px 0 4px;
  vertical-align: -2px;
}

.destaque__pessoas {
  margin: -8px 0 18px;
  font-size: 0.88rem;
  font-weight: 600;
  color: color-mix(in srgb, var(--chasque-ocre) 75%, var(--chasque-tinta));
}

.destaque__acoes {
  display: flex;
  align-items: center;
  gap: 20px;
}

.destaque__fui {
  color: var(--chasque-tinta);
  font-weight: 600;
  text-decoration: underline;
  text-decoration-color: var(--chasque-ocre);
  text-underline-offset: 4px;
}

.combina {
  display: block;
  margin-top: 4px;
  font-size: 0.82rem;
  color: var(--chasque-tinta);
}

.pessoas {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 3px;
  font-size: 0.8rem;
  font-weight: 600;
  color: color-mix(in srgb, var(--chasque-ocre) 75%, var(--chasque-tinta));
}

.salvo {
  flex: none;
  align-self: center;
  padding: 5px 10px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--chasque-ocre) 18%, transparent);
  color: var(--chasque-tinta);
  font-size: 0.75rem;
  font-weight: 700;
}

.rodape-sugestoes {
  margin: 18px 0 0;
  text-align: center;
}

.ajustar {
  border: 0;
  background: transparent;
  color: var(--chasque-tinta-suave);
  font: inherit;
  text-decoration: underline;
  text-underline-offset: 4px;
  padding: 10px;
}

.esqueleto {
  padding: 14px 16px;
}

.esqueleto__destaque {
  height: 190px;
  border-radius: 12px;
  margin: 0 0 18px;
}

.esqueleto__linha {
  height: 58px;
  border-radius: 14px;
  margin: 0 0 12px;
}

ion-skeleton-text {
  --background: var(--chasque-neblina);
  --background-rgb: 235, 228, 213;
}
</style>
