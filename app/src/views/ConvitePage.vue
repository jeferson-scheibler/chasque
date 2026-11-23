<template>
  <ion-page>
    <ion-content class="convite-pagina">
      <div class="centro">
        <ion-spinner v-if="carregando" name="crescent" />

        <template v-else-if="!dono">
          <h1>Convite inválido</h1>
          <p>Esse link pode ter sido trocado. Peça um link novo para a pessoa.</p>
          <router-link class="botao botao--noite botao--compacto" to="/abas/lugares" replace>Ir para o Chasque</router-link>
        </template>

        <template v-else>
          <iniciais :pessoa="dono" tamanho="g" />
          <h1>{{ titulo }}</h1>
          <p>{{ explicacao }}</p>

          <button v-if="estado === null" type="button" class="botao botao--sol" :disabled="enviando" @click="pedir">
            {{ enviando ? 'Enviando...' : `Pedir para seguir ${primeiroNome}` }}
          </button>
          <router-link
            v-else-if="estado === 'aceito'"
            class="botao botao--sol"
            :to="`/abas/conta/pessoas/${dono.id}`"
            replace
          >
            Ver as visitas de {{ primeiroNome }}
          </router-link>
          <router-link class="botao botao--texto" to="/abas/lugares" replace>
            {{ estado === null ? 'Agora não' : 'Ir para o Chasque' }}
          </router-link>
        </template>
      </div>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { IonContent, IonPage, IonSpinner, onIonViewWillEnter } from '@ionic/vue'
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import Iniciais from '@/components/Iniciais.vue'
import { api } from '@/services/api'
import type { Pessoa } from '@/types'

type Estado = null | 'pendente' | 'aceito' | 'proprio'

const route = useRoute()
const dono = ref<Pessoa | null>(null)
const estado = ref<Estado>(null)
const carregando = ref(true)
const enviando = ref(false)

const codigo = computed(() => String(route.params.codigo))
const primeiroNome = computed(() => dono.value?.nome.split(' ')[0] ?? '')
const titulo = computed(() => {
  if (estado.value === 'proprio') return 'Este é o seu convite'
  if (estado.value === 'pendente') return 'Pedido enviado'
  if (estado.value === 'aceito') return `Você segue ${primeiroNome.value}`
  return `${dono.value?.nome} quer compartilhar lugares com você`
})
const explicacao = computed(() => {
  if (estado.value === 'proprio') return 'Mande este link para quem você confia. Quem abrir pode pedir para seguir você.'
  if (estado.value === 'pendente') return `Quando ${primeiroNome.value} aceitar, as visitas compartilhadas aparecem para você.`
  if (estado.value === 'aceito') return `Você vê as visitas que ${primeiroNome.value} libera para pessoas de confiança.`
  return `Ao pedir para seguir, você passa a ver as visitas que ${primeiroNome.value} compartilhar, depois que o pedido for aceito. Suas visitas continuam só suas.`
})

async function carregar() {
  carregando.value = true
  try {
    const r = await api<{ pessoa: Pessoa; estado: Estado }>(`/convites/${encodeURIComponent(codigo.value)}/`)
    dono.value = r.pessoa
    estado.value = r.estado
  } catch {
    dono.value = null
  } finally {
    carregando.value = false
  }
}

async function pedir() {
  enviando.value = true
  try {
    const r = await api<{ estado: Estado }>(`/convites/${encodeURIComponent(codigo.value)}/`, { method: 'POST', json: {} })
    estado.value = r.estado
  } finally {
    enviando.value = false
  }
}

onIonViewWillEnter(carregar)
</script>

<style scoped>
.convite-pagina {
  --background: var(--chasque-faixa);
}

.centro {
  min-height: 100%;
  max-width: 420px;
  margin: 0 auto;
  padding: calc(env(safe-area-inset-top) + 18vh) 28px 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 14px;
  color: var(--chasque-faixa-texto);
}

h1 {
  margin: 10px 0 0;
  font-size: 1.7rem;
  font-weight: 650;
  line-height: 1.15;
  color: var(--chasque-faixa-texto);
}

p {
  margin: 0 0 12px;
  line-height: 1.5;
  color: var(--chasque-faixa-suave);
}

.botao--texto {
  color: var(--chasque-faixa-texto);
}

ion-spinner {
  color: var(--chasque-ocre);
}
</style>
