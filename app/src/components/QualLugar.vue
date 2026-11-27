<template>
  <div class="qual">
    <template v-if="!novo && (carregando || meus.length)">
      <h2 class="secao-titulo">{{ titulo }}</h2>

      <div v-if="sugerido" class="qual__parece cartao-rs">
        <span class="linha__icone"><ion-icon :icon="iconeDaCategoria(sugerido.categoria)" aria-hidden="true" /></span>
        <span class="linha__texto">
          <span class="qual__parece-rotulo">Pelo texto, parece ser</span>
          <span class="linha__titulo">{{ sugerido.nome }}</span>
          <span class="linha__meta">{{ resumoDoLugar(sugerido) || 'Lugar' }}</span>
        </span>
        <button type="button" class="botao botao--sol botao--compacto qual__esse-sim" @click="emit('escolher', sugerido)">
          É esse
        </button>
      </div>

      <button type="button" class="qual__novo" @click="novo = true">
        <span class="qual__sol" aria-hidden="true"><ion-icon :icon="addOutline" /></span>
        <span class="linha__texto">
          <span class="qual__novo-titulo">Iniciar um novo Chasque</span>
          <span class="qual__novo-meta">Lugar que ainda não está na sua lista</span>
        </span>
        <ion-icon :icon="arrowForward" class="qual__novo-seta" aria-hidden="true" />
      </button>

      <h3 class="secao-titulo qual__ou">Ou anexe a um lugar que você já tem</h3>
      <p class="secao-apoio">O link entra junto com os outros que você salvou dele.</p>

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
import { addOutline, arrowForward, searchOutline } from 'ionicons/icons'
import { computed, onMounted, ref } from 'vue'
import BuscaLugar from '@/components/BuscaLugar.vue'
import { iconeDaCategoria } from '@/categorias'
import { api } from '@/services/api'
import { resumoDoLugar, type Lugar, type MeuLugar } from '@/types'

const POUCOS = 5

const props = defineProps<{ titulo: string; sugestao?: string; ignorar?: number | null; sugerido?: Lugar | null }>()
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

/* mesmo bloco noturno do convite de fim de semana, com a divisa norte do RS no topo */
.qual__novo {
  display: flex;
  align-items: center;
  gap: 16px;
  width: calc(100% - 32px);
  margin: 10px 16px 0;
  padding: 24px 18px 18px;
  border: 0;
  border-radius: 6px 6px 20px 20px;
  background: var(--chasque-faixa);
  color: var(--chasque-faixa-texto);
  -webkit-mask: var(--borda-rs);
  mask: var(--borda-rs);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: transform 0.15s ease;
}

.qual__novo:active {
  transform: scale(0.985);
}

.qual__novo:focus-visible {
  outline: 3px solid var(--chasque-ocre);
  outline-offset: -6px;
}

.qual__sol {
  flex: none;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 24px;
  color: var(--chasque-sobre-ocre);
  background: var(--chasque-ocre);
  transition: transform 0.3s cubic-bezier(0.2, 0.9, 0.3, 1.4);
}

.qual__novo:active .qual__sol {
  transform: rotate(90deg);
}

.qual__novo-titulo {
  display: block;
  font-family: var(--chasque-fonte-titulo);
  font-size: 1.15rem;
  font-weight: 650;
  letter-spacing: -0.01em;
  line-height: 1.2;
}

.qual__novo-meta {
  display: block;
  margin-top: 3px;
  font-size: 0.85rem;
  color: var(--chasque-faixa-suave);
}

.qual__novo-seta {
  flex: none;
  margin-left: auto;
  font-size: 20px;
  color: var(--chasque-ocre);
  transition: transform 0.2s ease;
}

.qual__novo:active .qual__novo-seta {
  transform: translateX(4px);
}

/* o lugar que a IA achou no texto: a resposta pronta, antes das outras opções */
.qual__parece {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 6px 16px 0;
  padding: 20px 12px 12px 14px;
}

.qual__parece-rotulo {
  display: block;
  margin-bottom: 2px;
  font-size: 0.78rem;
  color: var(--chasque-tinta-suave);
}

.qual__esse-sim {
  flex: none;
  width: auto;
  padding: 0 16px;
}

.qual__ou {
  margin-top: 26px;
  font-size: 0.95rem;
  color: var(--chasque-tinta-suave);
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
