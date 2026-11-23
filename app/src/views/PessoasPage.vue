<template>
  <ion-page>
    <faixa titulo="Pessoas de confiança" subtitulo="Quem vê as visitas que você libera" voltar="/abas/conta" />

    <ion-content class="vale">
      <ion-refresher slot="fixed" @ion-refresh="atualizar($event)">
        <ion-refresher-content />
      </ion-refresher>

      <!-- Convite: a única forma de alguém pedir para seguir -->
      <section class="convite">
        <h2>Seu convite</h2>
        <p>
          Mande este link para quem você confia. A pessoa pede para te seguir e você decide. Ninguém acha você por
          nome ou e-mail.
        </p>
        <div class="convite__acoes">
          <button type="button" class="botao botao--sol" @click="compartilhar">
            <ion-icon :icon="shareSocialOutline" aria-hidden="true" />Mandar convite
          </button>
          <button type="button" class="botao botao--leve convite__copiar" aria-label="Copiar link" @click="copiar">
            <ion-icon :icon="copyOutline" aria-hidden="true" />
          </button>
        </div>
        <button type="button" class="trocar" @click="confirmarTroca">Trocar o link</button>
      </section>

      <section v-if="dados.pedidos.length">
        <h2 class="secao-titulo">Pedidos para seguir você</h2>
        <ul class="linhas">
          <li v-for="p in dados.pedidos" :key="p.id" class="linha pedido">
            <iniciais :pessoa="p.pessoa" />
            <span class="linha__texto"><span class="linha__titulo">{{ p.pessoa.nome }}</span></span>
            <button type="button" class="pequeno pequeno--sol" @click="aceitar(p)">Aceitar</button>
            <button type="button" class="pequeno" @click="desfazer(p.id, 'Pedido recusado')">Recusar</button>
          </li>
        </ul>
      </section>

      <section v-if="dados.seguindo.length">
        <h2 class="secao-titulo">Você segue</h2>
        <ul class="linhas">
          <li v-for="p in dados.seguindo" :key="p.id">
            <router-link :to="`/abas/conta/pessoas/${p.pessoa.id}`" class="linha">
              <iniciais :pessoa="p.pessoa" />
              <span class="linha__texto">
                <span class="linha__titulo">{{ p.pessoa.nome }}</span>
                <span class="linha__meta">{{ p.visitas ? `${p.visitas} ${p.visitas === 1 ? 'visita compartilhada' : 'visitas compartilhadas'}` : 'Ainda não compartilhou visitas' }}</span>
              </span>
              <ion-icon :icon="chevronForward" class="linha__seta" aria-hidden="true" />
            </router-link>
          </li>
        </ul>
      </section>

      <section v-if="dados.enviados.length">
        <h2 class="secao-titulo">Esperando aceitar</h2>
        <ul class="linhas">
          <li v-for="p in dados.enviados" :key="p.id" class="linha">
            <iniciais :pessoa="p.pessoa" />
            <span class="linha__texto">
              <span class="linha__titulo">{{ p.pessoa.nome }}</span>
              <span class="linha__meta">Pedido enviado</span>
            </span>
            <button type="button" class="pequeno" @click="desfazer(p.id, 'Pedido cancelado')">Cancelar</button>
          </li>
        </ul>
      </section>

      <section v-if="dados.seguidores.length">
        <h2 class="secao-titulo">Seguem você</h2>
        <p class="secao-apoio">Veem as visitas que você marca como "Pessoas de confiança".</p>
        <ul class="linhas">
          <li v-for="p in dados.seguidores" :key="p.id" class="linha">
            <iniciais :pessoa="p.pessoa" />
            <span class="linha__texto"><span class="linha__titulo">{{ p.pessoa.nome }}</span></span>
            <button type="button" class="pequeno" @click="confirmarRemocao(p)">Remover</button>
          </li>
        </ul>
      </section>

      <vazio
        v-if="carregou && vazio"
        pose="mate"
        titulo="Chimarrão se toma em roda"
        texto="Quando alguém aceitar seu convite, ou você aceitar o de alguém, essa pessoa aparece aqui."
      />
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import {
  alertController, IonContent, IonIcon, IonPage, IonRefresher, IonRefresherContent, onIonViewWillEnter,
  toastController, type RefresherCustomEvent,
} from '@ionic/vue'
import { chevronForward, copyOutline, shareSocialOutline } from 'ionicons/icons'
import { computed, ref } from 'vue'
import Faixa from '@/components/Faixa.vue'
import Iniciais from '@/components/Iniciais.vue'
import Vazio from '@/components/Vazio.vue'
import { api } from '@/services/api'
import { useSessao } from '@/stores/sessao'
import type { Pessoa } from '@/types'

interface Ligacao {
  id: number
  pessoa: Pessoa
  visitas?: number
}
interface Tela {
  convite: string
  pedidos: Ligacao[]
  seguindo: Ligacao[]
  enviados: Ligacao[]
  seguidores: Ligacao[]
}

const sessao = useSessao()
const dados = ref<Tela>({ convite: '', pedidos: [], seguindo: [], enviados: [], seguidores: [] })
const carregou = ref(false)
const vazio = computed(() => ['pedidos', 'seguindo', 'enviados', 'seguidores'].every((k) => !dados.value[k as keyof Tela].length))
const link = computed(() => `${location.origin}/convite/${dados.value.convite}`)

async function avisar(mensagem: string, cor?: string) {
  const toast = await toastController.create({ message: mensagem, duration: 2400, color: cor, position: 'top' })
  await toast.present()
}

async function carregar() {
  try {
    dados.value = await api<Tela>('/pessoas/')
  } finally {
    carregou.value = true
  }
}

async function atualizar(evento: RefresherCustomEvent) {
  await carregar()
  await evento.target.complete()
}

async function compartilhar() {
  const nome = sessao.usuario?.nome?.split(' ')[0] ?? 'Eu'
  const texto = `${nome} quer compartilhar os lugares favoritos com você no Chasque.`
  if (navigator.share) {
    try {
      await navigator.share({ title: 'Convite do Chasque', text: texto, url: link.value })
      return
    } catch {
      // cancelou o menu do celular: tudo bem
      return
    }
  }
  await copiar()
}

async function copiar() {
  try {
    await navigator.clipboard.writeText(link.value)
    await avisar('Link copiado')
  } catch {
    await avisar(link.value)
  }
}

async function confirmarTroca() {
  const alerta = await alertController.create({
    header: 'Trocar o link?',
    message: 'Quem tem o link atual não vai mais conseguir pedir para seguir você. Quem já segue continua.',
    buttons: [
      { text: 'Cancelar', role: 'cancel' },
      {
        text: 'Trocar',
        handler: () => {
          void api<{ convite: string }>('/pessoas/convite/novo/', { method: 'POST', json: {} }).then((r) => {
            dados.value.convite = r.convite
            void avisar('Link trocado')
          })
        },
      },
    ],
  })
  await alerta.present()
}

async function aceitar(p: Ligacao) {
  await api(`/confiancas/${p.id}/aceitar/`, { method: 'POST', json: {} })
  await carregar()
  await avisar(`${p.pessoa.nome} agora segue você`)
}

async function desfazer(id: number, mensagem: string) {
  await api(`/confiancas/${id}/`, { method: 'DELETE' })
  await carregar()
  await avisar(mensagem)
}

async function confirmarRemocao(p: Ligacao) {
  const alerta = await alertController.create({
    header: `Remover ${p.pessoa.nome}?`,
    message: 'A pessoa deixa de ver as suas visitas. Ninguém recebe aviso.',
    buttons: [
      { text: 'Cancelar', role: 'cancel' },
      { text: 'Remover', role: 'destructive', handler: () => { void desfazer(p.id, 'Pessoa removida') } },
    ],
  })
  await alerta.present()
}

onIonViewWillEnter(carregar)
</script>

<style scoped>
.convite {
  position: relative;
  overflow: hidden;
  margin: 8px 16px 6px;
  padding: 20px;
  border-radius: 24px;
  background: var(--chasque-faixa);
  color: var(--chasque-faixa-texto);
}

@media (prefers-color-scheme: dark) {
  .convite {
    background: #1a2440;
    border: 1px solid var(--chasque-neblina);
  }
}

.convite h2 {
  margin: 0 0 6px;
  font-size: 1.3rem;
  font-weight: 650;
  color: var(--chasque-faixa-texto);
}

.convite p {
  margin: 0 0 16px;
  line-height: 1.45;
  color: var(--chasque-faixa-suave);
}

.convite__acoes {
  display: flex;
  gap: 10px;
}

.convite__copiar {
  flex: none;
  width: 54px;
  padding: 0;
  border-color: var(--chasque-faixa-vidro);
  color: var(--chasque-faixa-texto);
}

.trocar {
  margin-top: 10px;
  padding: 6px 0;
  border: 0;
  background: transparent;
  color: var(--chasque-faixa-suave);
  font: inherit;
  font-size: 0.85rem;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.linha {
  cursor: default;
}

a.linha {
  cursor: pointer;
}

.pequeno {
  flex: none;
  height: 36px;
  padding: 0 13px;
  border-radius: 999px;
  border: 1.5px solid var(--chasque-neblina);
  background: transparent;
  color: var(--chasque-tinta);
  font: inherit;
  font-size: 0.85rem;
  font-weight: 600;
}

.pequeno--sol {
  border-color: var(--chasque-ocre);
  background: var(--chasque-ocre);
  color: var(--chasque-sobre-ocre);
}

</style>
