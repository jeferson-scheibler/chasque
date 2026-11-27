<template>
  <!-- Por que a pessoa salvou: a frase lida pela IA (ou escrita por ela), para voltar no dia do passeio. -->
  <div class="intencao">
    <div v-if="editando" class="intencao__bloco cartao-rs">
      <label class="intencao__campo">
        <span>O motivo, em uma frase</span>
        <input v-model="frase" type="text" maxlength="120" placeholder="Pizza de fermentação natural" />
      </label>
      <p class="intencao__apoio">Até 3 motivos{{ tags.length ? `: ${tags.length} marcado${tags.length > 1 ? 's' : ''}` : '' }}</p>
      <template v-for="grupo in grupos" :key="grupo.nome">
        <h3 class="intencao__grupo">{{ grupo.nome }}</h3>
        <escolhas :model-value="tags" :opcoes="grupo.opcoes" multipla :rotulo="grupo.nome" @update:model-value="marcar" />
      </template>
      <div class="intencao__acoes">
        <button type="button" class="botao botao--noite botao--compacto" :disabled="salvando" @click="confirmar(frase, tags)">
          Salvar motivo
        </button>
        <button type="button" class="botao botao--texto" @click="editando = false">Cancelar</button>
      </div>
    </div>

    <div v-else-if="intencao?.estado === 'pendente'" class="intencao__bloco intencao__bloco--lendo cartao-rs">
      <p class="intencao__lendo">O Chasque está lendo o seu texto para guardar o motivo em uma frase.</p>
    </div>

    <div v-else-if="temMotivo" class="intencao__bloco cartao-rs">
      <p class="intencao__frase">{{ intencao!.frase || 'Sem frase, só os motivos' }}</p>
      <ul v-if="intencao!.tags.length" class="intencao__tags" aria-label="Motivos">
        <li v-for="slug in intencao!.tags" :key="slug">{{ motivos.nome(slug) }}</li>
      </ul>
      <template v-if="intencao!.estado === 'pronta'">
        <p class="intencao__origem">Lido do seu texto pela IA. Confira:</p>
        <div class="intencao__acoes">
          <button type="button" class="botao botao--noite botao--compacto" :disabled="salvando" @click="confirmar(intencao!.frase, intencao!.tags)">
            Está certo
          </button>
          <button type="button" class="botao botao--texto" @click="abrirEdicao">Corrigir</button>
          <button type="button" class="botao botao--texto" :disabled="salvando" @click="confirmar('', [])">Não é isso</button>
        </div>
      </template>
      <button v-else type="button" class="botao botao--texto intencao__corrigir" @click="abrirEdicao">Corrigir o motivo</button>
    </div>

    <div v-else-if="convidar" class="intencao__bloco cartao-rs">
      <p class="intencao__convite">
        O Chasque pode ler esse texto e guardar o motivo em uma frase, para lembrar você no dia do passeio.
      </p>
      <p class="intencao__origem">O texto vai para a IA do Google. Seu nome e e-mail, não.</p>
      <div class="intencao__acoes">
        <button type="button" class="botao botao--noite botao--compacto" :disabled="salvando" @click="ligarLeitura">
          Ligar a leitura
        </button>
        <button type="button" class="botao botao--texto" @click="dispensarConvite">Agora não</button>
      </div>
    </div>

    <button v-else type="button" class="botao botao--texto intencao__escrever" @click="abrirEdicao">
      Resumir o motivo em uma frase
    </button>
  </div>
</template>

<script setup lang="ts">
import { toastController } from '@ionic/vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Escolhas from '@/components/Escolhas.vue'
import { api, ErroApi } from '@/services/api'
import { useMotivos } from '@/stores/motivos'
import { useSessao } from '@/stores/sessao'
import type { Salvo } from '@/types'

const MAX_TAGS = 3
const CHAVE_CONVITE = 'chasque:convite-ia-dispensado'
// O leitor roda a cada minuto: olha de novo algumas vezes enquanto a leitura está na fila.
const INTERVALO_MS = 15000
const MAX_CONSULTAS = 8

const props = defineProps<{ salvo: Salvo }>()
const emit = defineEmits<{ atualizado: [salvo: Salvo] }>()

const sessao = useSessao()
const motivos = useMotivos()
const editando = ref(false)
const salvando = ref(false)
const frase = ref('')
const tags = ref<string[]>([])
const conviteDispensado = ref(lerDispensa())

const intencao = computed(() => props.salvo.intencao)
const temMotivo = computed(() => !!intencao.value && (!!intencao.value.frase || intencao.value.tags.length > 0))
const convidar = computed(
  () => !!props.salvo.texto.trim() && !intencao.value && sessao.usuario?.usar_ia === false && !conviteDispensado.value,
)
const grupos = computed(() =>
  motivos.grupos.map((g) => ({ nome: g.nome, opcoes: g.motivos.map((m) => ({ valor: m.slug, rotulo: m.nome })) })),
)

function lerDispensa() {
  try {
    return localStorage.getItem(CHAVE_CONVITE) === '1'
  } catch {
    return false
  }
}

function dispensarConvite() {
  conviteDispensado.value = true
  try {
    localStorage.setItem(CHAVE_CONVITE, '1')
  } catch {
    // sem armazenamento, o convite só some nesta visita
  }
}

async function avisar(mensagem: string, cor?: string) {
  const toast = await toastController.create({ message: mensagem, duration: 2400, color: cor, position: 'top' })
  await toast.present()
}

/** Marcar o quarto motivo tira o mais antigo: ficam sempre os 3 últimos. */
function marcar(valor: string[] | string) {
  const lista = Array.isArray(valor) ? valor : [valor]
  tags.value = lista.slice(-MAX_TAGS)
}

function abrirEdicao() {
  frase.value = intencao.value?.frase ?? ''
  tags.value = [...(intencao.value?.tags ?? [])]
  editando.value = true
  void motivos.carregar()
}

async function confirmar(novaFrase: string, novasTags: string[]) {
  salvando.value = true
  try {
    const salvo = await api<Salvo>(`/salvos/${props.salvo.id}/intencao/`, {
      method: 'PUT',
      json: { frase: novaFrase.trim(), tags: novasTags },
    })
    emit('atualizado', salvo)
    editando.value = false
    await avisar(novaFrase.trim() || novasTags.length ? 'Motivo guardado' : 'Motivo descartado')
  } catch (e) {
    await avisar(e instanceof ErroApi ? e.message : 'Não foi possível salvar o motivo.', 'danger')
  } finally {
    salvando.value = false
  }
}

async function ligarLeitura() {
  salvando.value = true
  try {
    await sessao.atualizar({ usar_ia: true })
    emit('atualizado', await api<Salvo>(`/salvos/${props.salvo.id}/`))
  } catch {
    await avisar('Não foi possível ligar a leitura.', 'danger')
  } finally {
    salvando.value = false
  }
}

let espera: ReturnType<typeof setTimeout> | undefined
let consultas = 0

function acompanhar() {
  clearTimeout(espera)
  if (intencao.value?.estado !== 'pendente' || consultas >= MAX_CONSULTAS) return
  espera = setTimeout(async () => {
    consultas += 1
    try {
      emit('atualizado', await api<Salvo>(`/salvos/${props.salvo.id}/`))
    } catch {
      // tenta de novo na próxima volta
    }
    acompanhar()
  }, INTERVALO_MS)
}

watch(() => intencao.value?.estado, (estado, antes) => {
  if (estado === 'pendente' && antes !== 'pendente') consultas = 0
  acompanhar()
})
onMounted(() => {
  void motivos.carregar()
  acompanhar()
})
onBeforeUnmount(() => clearTimeout(espera))
</script>

<style scoped>
.intencao {
  margin: 8px 16px 0;
}

.intencao__bloco {
  padding: 24px 16px 16px;
}

.intencao__frase {
  margin: 0;
  font-family: var(--chasque-fonte-titulo);
  font-size: 1.25rem;
  font-weight: 650;
  line-height: 1.25;
  letter-spacing: -0.01em;
  color: var(--chasque-tinta);
  text-wrap: balance;
}

.intencao__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
}

.intencao__tags li {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--chasque-tinta);
  background: color-mix(in srgb, var(--chasque-ocre) 18%, transparent);
}

.intencao__origem,
.intencao__apoio {
  margin: 12px 0 0;
  font-size: 0.82rem;
  color: var(--chasque-tinta-suave);
}

.intencao__lendo,
.intencao__convite {
  margin: 0;
  line-height: 1.45;
  color: var(--chasque-tinta);
}

.intencao__lendo {
  color: var(--chasque-tinta-suave);
}

.intencao__acoes {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 14px;
  margin-top: 12px;
}

.intencao__acoes .botao {
  width: auto;
}

.intencao__acoes .botao--compacto {
  padding: 0 18px;
}

.intencao__acoes .botao--texto,
.intencao__corrigir,
.intencao__escrever {
  width: auto;
  padding: 0;
  color: var(--chasque-tinta-suave);
  text-decoration: underline;
  text-underline-offset: 4px;
}

.intencao__corrigir {
  margin-top: 10px;
}

.intencao__escrever {
  margin: 2px 4px 0;
}

.intencao__campo {
  display: grid;
  gap: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--chasque-tinta);
}

.intencao__campo input {
  height: 46px;
  padding: 0 14px;
  border: 1px solid var(--chasque-neblina);
  border-radius: 14px;
  background: var(--chasque-fundo);
  font: inherit;
  font-weight: 400;
  color: var(--chasque-tinta);
  outline: none;
}

.intencao__campo input:focus-visible {
  border-color: var(--chasque-ocre);
}

.intencao__grupo {
  margin: 14px 0 8px;
  font-size: 0.8rem;
  font-weight: 650;
  color: var(--chasque-tinta-suave);
}
</style>
