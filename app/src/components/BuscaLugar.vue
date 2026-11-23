<template>
  <div class="busca">
    <template v-if="!cadastrando">
      <div class="busca__campo">
        <ion-icon :icon="searchOutline" aria-hidden="true" />
        <input
          v-model="termo"
          type="search"
          enterkeyhint="search"
          autocomplete="off"
          placeholder="Nome do lugar, ex.: cachoeira, café"
          aria-label="Buscar lugar"
          @input="agendarBusca"
        />
        <ion-spinner v-if="carregando" name="crescent" />
      </div>

      <ul v-if="resultados.length" class="linhas busca__resultados">
        <li v-for="lugar in resultados" :key="lugar.id">
          <button type="button" class="linha" @click="emit('escolher', lugar)">
            <span class="linha__icone"><ion-icon :icon="iconeDaCategoria(lugar.categoria)" aria-hidden="true" /></span>
            <span class="linha__texto">
              <span class="linha__titulo">{{ lugar.nome }}</span>
              <span class="linha__meta">{{ resumoDoLugar(lugar) || 'Lugar cadastrado' }}{{ lugar.endereco ? `. ${lugar.endereco}` : '' }}</span>
            </span>
            <span class="busca__escolher">Esse</span>
          </button>
        </li>
      </ul>

      <p v-else-if="buscou && !carregando" class="busca__nada">Nenhum lugar com esse nome na base ainda.</p>

      <button v-if="buscou && !carregando" type="button" class="linha busca__novo" @click="abrirCadastro">
        <span class="linha__icone"><ion-icon :icon="addOutline" aria-hidden="true" /></span>
        <span class="linha__texto">
          <span class="linha__titulo">Cadastrar "{{ termo.trim() }}"</span>
          <span class="linha__meta">Não achou? Adicione o lugar à base.</span>
        </span>
      </button>

      <p class="busca__atribuicao">
        Lugares do
        <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>,
        mantido por colaboradores.
      </p>
    </template>

    <form v-else class="busca__cadastro" novalidate @submit.prevent="cadastrar">
      <campo v-model="novo.nome" rotulo="Nome do lugar" :maxlength="200" />
      <escolher-cidade v-model="novo.cidadeId" :cidades="cidades" />
      <campo v-model="novo.endereco" rotulo="Endereço (opcional)" :maxlength="300" />

      <button type="button" class="localizar" :class="{ 'localizar--ok': posicao }" :disabled="localizando" @click="usarLocalizacao">
        <ion-icon :icon="posicao ? checkmarkCircle : locateOutline" aria-hidden="true" />
        <span>
          <strong>{{ localizando ? 'Localizando...' : posicao ? 'Localização capturada' : 'Estou nesse lugar agora' }}</strong>
          <small>{{ posicao ? 'O lugar fica no ponto exato onde você está.' : 'Sem isso, o lugar fica no centro da cidade.' }}</small>
        </span>
      </button>

      <p v-if="erro" class="mensagem-erro" role="alert">{{ erro }}</p>

      <button type="submit" class="botao botao--noite" :disabled="salvando">
        {{ salvando ? 'Cadastrando...' : 'Cadastrar e ligar ao link' }}
      </button>
      <button type="button" class="botao botao--texto" @click="cadastrando = false">Voltar para a busca</button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { IonIcon, IonSpinner } from '@ionic/vue'
import { addOutline, checkmarkCircle, locateOutline, searchOutline } from 'ionicons/icons'
import { onMounted, reactive, ref } from 'vue'
import Campo from '@/components/Campo.vue'
import EscolherCidade from '@/components/EscolherCidade.vue'
import { iconeDaCategoria } from '@/categorias'
import { api, ErroApi } from '@/services/api'
import { resumoDoLugar, type Cidade, type Lugar } from '@/types'

const props = defineProps<{ sugestao?: string }>()
const emit = defineEmits<{ escolher: [lugar: Lugar] }>()

const termo = ref(props.sugestao ?? '')
const resultados = ref<Lugar[]>([])
const carregando = ref(false)
const buscou = ref(false)

const cadastrando = ref(false)
const cidades = ref<Cidade[]>([])
const novo = reactive({ nome: '', cidadeId: null as number | null, endereco: '' })
const posicao = ref<{ lat: number; lng: number } | null>(null)
const localizando = ref(false)
const salvando = ref(false)
const erro = ref('')

let ultimaBusca = 0
let espera: ReturnType<typeof setTimeout> | undefined

function agendarBusca() {
  clearTimeout(espera)
  espera = setTimeout(buscar, 280)
}

async function buscar() {
  const q = termo.value.trim()
  if (q.length < 2) {
    resultados.value = []
    buscou.value = false
    return
  }
  const esta = ++ultimaBusca
  carregando.value = true
  try {
    const achados = await api<Lugar[]>(`/lugares/?q=${encodeURIComponent(q)}`)
    if (esta === ultimaBusca) resultados.value = achados
  } catch {
    if (esta === ultimaBusca) resultados.value = []
  } finally {
    if (esta === ultimaBusca) {
      carregando.value = false
      buscou.value = true
    }
  }
}

async function abrirCadastro() {
  novo.nome = termo.value.trim()
  erro.value = ''
  cadastrando.value = true
  if (cidades.value.length === 0) {
    try {
      cidades.value = await api<Cidade[]>('/cidades/')
    } catch {
      erro.value = 'Não foi possível carregar as cidades.'
    }
  }
}

function usarLocalizacao() {
  if (!('geolocation' in navigator)) {
    erro.value = 'Este aparelho não informa a localização. Escolha a cidade.'
    return
  }
  localizando.value = true
  erro.value = ''
  // Só pede a posição quando a pessoa toca no botão; nada roda em segundo plano.
  navigator.geolocation.getCurrentPosition(
    (p) => {
      posicao.value = { lat: p.coords.latitude, lng: p.coords.longitude }
      localizando.value = false
    },
    () => {
      erro.value = 'Não deu para pegar a localização. Escolha a cidade.'
      localizando.value = false
    },
    { enableHighAccuracy: true, timeout: 15000 },
  )
}

async function cadastrar() {
  erro.value = ''
  if (novo.nome.trim().length < 2) {
    erro.value = 'Escreva o nome do lugar.'
    return
  }
  if (!posicao.value && !novo.cidadeId) {
    erro.value = 'Escolha a cidade ou use a sua localização.'
    return
  }
  salvando.value = true
  try {
    const lugar = await api<Lugar>('/lugares/', {
      method: 'POST',
      json: {
        nome: novo.nome,
        endereco: novo.endereco,
        ...(novo.cidadeId ? { cidade_id: novo.cidadeId } : {}),
        ...(posicao.value ?? {}),
      },
    })
    emit('escolher', lugar)
  } catch (e) {
    erro.value = e instanceof ErroApi && e.status === 429
      ? 'Você já cadastrou muitos lugares hoje. Tente amanhã.'
      : e instanceof ErroApi ? e.message : 'Sem conexão com o servidor.'
  } finally {
    salvando.value = false
  }
}

onMounted(() => {
  if (termo.value.trim().length >= 2) void buscar()
})
</script>

<style scoped>
.busca__campo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 16px;
  padding: 0 14px;
  height: 52px;
  border-radius: 16px;
  background: var(--chasque-papel);
  border: 1.5px solid var(--chasque-neblina);
  color: var(--chasque-tinta-suave);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.busca__campo:focus-within {
  border-color: var(--chasque-faixa);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--chasque-faixa) 12%, transparent);
}

.busca__campo ion-icon {
  font-size: 20px;
  flex: none;
}

.busca__campo input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  font: inherit;
  font-size: 1rem;
  color: var(--chasque-tinta);
}

.busca__campo ion-spinner {
  width: 20px;
  height: 20px;
  color: var(--chasque-ocre);
}

.busca__resultados {
  margin-top: 6px;
}

.busca__escolher {
  flex: none;
  padding: 7px 12px;
  border-radius: 999px;
  border: 1.5px solid var(--chasque-neblina);
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--chasque-tinta);
}

.busca__nada {
  margin: 16px 20px 4px;
  color: var(--chasque-tinta-suave);
}

.busca__novo .linha__icone {
  background: transparent;
  border: 1.5px dashed var(--chasque-tinta-suave);
}

.busca__atribuicao {
  margin: 12px 20px 0;
  font-size: 0.75rem;
  color: var(--chasque-tinta-suave);
}

.busca__atribuicao a {
  color: inherit;
}

.busca__cadastro {
  padding: 0 20px;
}

.localizar {
  display: flex;
  gap: 12px;
  align-items: center;
  width: 100%;
  margin: 0 0 18px;
  padding: 14px;
  border-radius: 16px;
  border: 1.5px dashed var(--chasque-neblina);
  background: transparent;
  color: var(--chasque-tinta);
  font: inherit;
  text-align: left;
}

.localizar ion-icon {
  flex: none;
  font-size: 24px;
  color: var(--chasque-ocre);
}

.localizar strong {
  display: block;
  font-weight: 600;
}

.localizar small {
  display: block;
  margin-top: 2px;
  font-size: 0.82rem;
  color: var(--chasque-tinta-suave);
}

.localizar--ok {
  border-style: solid;
  border-color: var(--ion-color-success);
}

.localizar--ok ion-icon {
  color: var(--ion-color-success);
}
</style>
