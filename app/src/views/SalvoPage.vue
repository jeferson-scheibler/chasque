<template>
  <ion-page>
    <faixa :titulo="titulo" :subtitulo="subtitulo" voltar="/abas/lugares" />

    <ion-content class="vale">
      <div v-if="carregando" class="ion-padding ion-text-center"><ion-spinner name="crescent" /></div>

      <vazio
        v-else-if="!salvo"
        pose="duvida"
        titulo="Esse link não está mais aqui"
        texto="Ele pode ter sido removido. Volte para Meus lugares para ver o que está salvo."
      />

      <template v-else>
        <a class="origem" :href="salvo.url" target="_blank" rel="noopener noreferrer">
          <span class="origem__icone"><ion-icon :icon="logoInstagram" aria-hidden="true" /></span>
          <span class="linha__texto">
            <span class="linha__titulo">{{ NOME_DO_TIPO[salvo.tipo] }}</span>
            <span class="linha__meta">{{ salvo.perfil ? `@${salvo.perfil}, abrir no Instagram` : 'Abrir no Instagram' }}</span>
          </span>
          <ion-icon :icon="openOutline" class="linha__seta" aria-hidden="true" />
        </a>

        <section v-if="salvo.lugar && !trocando" class="lugar">
          <div class="lugar__cabeca">
            <span class="lugar__icone"><ion-icon :icon="iconeDaCategoria(salvo.lugar.categoria)" aria-hidden="true" /></span>
            <div>
              <p class="lugar__onde">{{ resumoDoLugar(salvo.lugar) || 'Lugar' }}</p>
              <p v-if="salvo.lugar.endereco" class="lugar__endereco">{{ salvo.lugar.endereco }}</p>
              <p v-if="salvo.lugar.aproximado" class="lugar__endereco">Posição aproximada, no centro da cidade.</p>
            </div>
          </div>
          <ul v-if="motivosDoLugar.length" class="motivos" aria-label="Motivos do lugar">
            <li v-for="m in motivosDoLugar" :key="m.slug" :class="{ comunidade: m.pessoas }">
              {{ nomeDaTag(m.slug) }}
              <span v-if="m.pessoas" class="motivos__pessoas" :aria-label="`marcado por ${m.pessoas} pessoas`">
                <ion-icon :icon="peopleOutline" aria-hidden="true" />{{ m.pessoas }}
              </span>
            </li>
          </ul>
          <p v-if="salvo.lugar.motivos_comunidade.length" class="motivos__nota">
            Os números mostram quantas pessoas marcaram o motivo em visitas que avaliaram bem.
          </p>
          <router-link class="botao botao--sol visitei" :to="{ path: '/abas/lugares/visita/nova', query: { salvo: salvo.id } }">
            <ion-icon :icon="footstepsOutline" aria-hidden="true" />{{ salvo.visitado ? 'Registrar outra visita' : 'Já fui, registrar visita' }}
          </router-link>
          <button type="button" class="botao botao--texto" @click="trocando = true">Não é esse lugar</button>
        </section>

        <section v-else class="identificar">
          <h2 class="secao-titulo">{{ trocando ? 'Qual é o lugar certo?' : 'Encontre o lugar' }}</h2>
          <p class="secao-apoio">Busque pelo nome. A base tem os lugares do Rio Grande do Sul.</p>
          <busca-lugar :sugestao="sugestao" @escolher="vincular" />
          <button v-if="trocando" type="button" class="botao botao--texto" @click="trocando = false">Cancelar</button>
        </section>

        <section class="anotacao">
          <h2 class="secao-titulo">Por que quer ir</h2>
          <textarea
            v-model="texto"
            class="anotacao__papel"
            rows="4"
            maxlength="2000"
            placeholder="Cole a legenda do post ou escreva o que chamou sua atenção."
            aria-label="Anotação"
          />
          <button v-if="texto !== salvo.texto" type="button" class="botao botao--noite anotacao__salvar" @click="salvarTexto">
            Salvar anotação
          </button>
        </section>

        <button type="button" class="botao botao--perigo remover" @click="confirmarRemocao">
          <ion-icon :icon="trashOutline" aria-hidden="true" />Remover dos salvos
        </button>
      </template>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { alertController, IonContent, IonIcon, IonPage, IonSpinner, toastController } from '@ionic/vue'
import { footstepsOutline, logoInstagram, openOutline, peopleOutline, trashOutline } from 'ionicons/icons'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BuscaLugar from '@/components/BuscaLugar.vue'
import Faixa from '@/components/Faixa.vue'
import Vazio from '@/components/Vazio.vue'
import { iconeDaCategoria, nomeDaTag } from '@/categorias'
import { api, ErroApi } from '@/services/api'
import { NOME_DO_TIPO, resumoDoLugar, type Lugar, type Salvo } from '@/types'

const route = useRoute()
const router = useRouter()

const salvo = ref<Salvo | null>(null)
const carregando = ref(true)
const trocando = ref(false)
const texto = ref('')

const caminho = computed(() => `/salvos/${route.params.id}/`)
// motivos confirmados por pessoas primeiro, depois os do OpenStreetMap
const motivosDoLugar = computed(() => {
  const lugar = salvo.value?.lugar
  if (!lugar) return []
  const daComunidade = lugar.motivos_comunidade.map((m) => ({ slug: m.slug, pessoas: m.pessoas }))
  const vistos = new Set(daComunidade.map((m) => m.slug))
  return [...daComunidade, ...lugar.tags.filter((s) => !vistos.has(s)).map((slug) => ({ slug, pessoas: 0 }))]
})
const titulo = computed(() => (carregando.value ? '' : salvo.value?.lugar?.nome ?? 'Qual lugar é esse?'))
const subtitulo = computed(() => (salvo.value ? `Salvo do Instagram` : undefined))
// "cafe.da_praca" vira "cafe da praca" para começar a busca.
const sugestao = computed(() => (salvo.value?.perfil ?? '').replace(/[._]+/g, ' ').trim())

async function avisar(mensagem: string, cor?: string) {
  const toast = await toastController.create({ message: mensagem, duration: 2400, color: cor, position: 'top' })
  await toast.present()
}

async function carregar() {
  carregando.value = true
  try {
    salvo.value = await api<Salvo>(caminho.value)
    texto.value = salvo.value.texto
  } catch {
    salvo.value = null
  } finally {
    carregando.value = false
  }
}

async function atualizar(dados: Record<string, unknown>) {
  salvo.value = await api<Salvo>(caminho.value, { method: 'PATCH', json: dados })
}

async function vincular(lugar: Lugar) {
  try {
    await atualizar({ lugar_id: lugar.id })
    trocando.value = false
    await avisar(`Ligado a ${lugar.nome}`)
  } catch (e) {
    await avisar(e instanceof ErroApi ? e.message : 'Não foi possível ligar ao lugar.', 'danger')
  }
}

async function salvarTexto() {
  try {
    await atualizar({ texto: texto.value })
    await avisar('Anotação salva')
  } catch (e) {
    await avisar(e instanceof ErroApi ? e.message : 'Não foi possível salvar.', 'danger')
  }
}

async function confirmarRemocao() {
  const alerta = await alertController.create({
    header: 'Remover dos salvos?',
    message: 'O link sai da sua lista. O lugar continua na base do Chasque.',
    buttons: [
      { text: 'Cancelar', role: 'cancel' },
      { text: 'Remover', role: 'destructive', handler: () => { void remover() } },
    ],
  })
  await alerta.present()
}

async function remover() {
  try {
    await api(caminho.value, { method: 'DELETE' })
    await router.replace('/abas/lugares')
    await avisar('Removido dos salvos')
  } catch {
    await avisar('Não foi possível remover.', 'danger')
  }
}

onMounted(carregar)
</script>

<style scoped>
.origem {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 6px 16px 0;
  padding: 14px 16px;
  border-radius: 18px;
  background: var(--chasque-papel);
  border: 1px solid var(--chasque-neblina);
  color: inherit;
  text-decoration: none;
}

.origem__icone {
  flex: none;
  width: 42px;
  height: 42px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  font-size: 22px;
  color: var(--chasque-sobre-ocre);
  background: var(--chasque-ocre);
}

.lugar {
  padding: 22px 20px 0;
}

.lugar__cabeca {
  display: flex;
  gap: 16px;
  align-items: center;
}

.lugar__icone {
  flex: none;
  width: 64px;
  height: 64px;
  border-radius: 20px;
  display: grid;
  place-items: center;
  font-size: 30px;
  background: var(--chasque-faixa);
  color: var(--chasque-faixa-texto);
}

.lugar__onde {
  margin: 0;
  font-family: var(--chasque-fonte-titulo);
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--chasque-tinta);
}

.lugar__endereco {
  margin: 3px 0 0;
  font-size: 0.9rem;
  color: var(--chasque-tinta-suave);
}

.motivos {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 18px 0 4px;
  padding: 0;
  list-style: none;
}

.motivos li {
  padding: 7px 12px;
  border-radius: 999px;
  background: var(--chasque-neblina);
  color: var(--chasque-tinta);
  font-size: 0.85rem;
  font-weight: 500;
}

.visitei {
  margin-top: 18px;
}

.motivos li.comunidade {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: color-mix(in srgb, var(--chasque-ocre) 22%, var(--chasque-fundo));
}

.motivos__pessoas {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 0.78rem;
  font-weight: 700;
}

.motivos__nota {
  margin: 0 0 4px;
  font-size: 0.8rem;
  color: var(--chasque-tinta-suave);
}

.lugar .botao--texto {
  width: auto;
  padding: 0;
  margin-top: 6px;
  color: var(--chasque-tinta-suave);
  text-decoration: underline;
  text-underline-offset: 4px;
}

.identificar .botao--texto {
  margin-top: 8px;
}

.anotacao {
  padding-bottom: 4px;
}

/* papel pautado: a anotação é um recado escrito à mão */
.anotacao__papel {
  display: block;
  width: calc(100% - 32px);
  margin: 8px 16px 0;
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

.anotacao__papel:focus {
  border-color: var(--chasque-faixa);
}

.anotacao__salvar {
  width: calc(100% - 32px);
  margin: 12px 16px 0;
}

.remover {
  margin: 28px auto 0;
  width: auto;
  padding: 0 18px;
}
</style>
