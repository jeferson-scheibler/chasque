<template>
  <ion-page>
    <ion-content class="ion-padding">
      <form class="formulario" @submit.prevent="enviar">
        <h1 class="marca">Chasque</h1>
        <p class="texto-apoio">Guarde por que gostou de cada lugar.</p>

        <ion-list lines="full">
          <ion-item>
            <ion-input v-model="email" label="E-mail" label-placement="stacked" type="email" autocomplete="email" inputmode="email" required />
          </ion-item>
          <ion-item>
            <ion-input v-model="senha" label="Senha" label-placement="stacked" type="password" autocomplete="current-password" required>
              <ion-input-password-toggle slot="end" />
            </ion-input>
          </ion-item>
        </ion-list>

        <ion-text v-if="erro" color="danger"><p role="alert">{{ erro }}</p></ion-text>

        <ion-button expand="block" type="submit" class="ion-margin-top" :disabled="enviando">
          {{ enviando ? 'Entrando...' : 'Entrar' }}
        </ion-button>
        <ion-button expand="block" fill="clear" router-link="/cadastro">Criar conta</ion-button>
      </form>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { IonButton, IonContent, IonInput, IonInputPasswordToggle, IonItem, IonList, IonPage, IonText } from '@ionic/vue'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ErroApi } from '@/services/api'
import { useSessao } from '@/stores/sessao'

const sessao = useSessao()
const router = useRouter()
const route = useRoute()

const email = ref('')
const senha = ref('')
const erro = ref('')
const enviando = ref(false)

async function enviar() {
  erro.value = ''
  enviando.value = true
  try {
    await sessao.entrar(email.value, senha.value)
    const volta = typeof route.query.volta === 'string' && route.query.volta.startsWith('/') && !route.query.volta.startsWith('//') ? route.query.volta : '/abas/sugestoes'
    await router.replace(volta)
  } catch (e) {
    erro.value = e instanceof ErroApi && e.status === 429
      ? 'Muitas tentativas. Espere um minuto e tente de novo.'
      : e instanceof ErroApi ? e.message : 'Sem conexão com o servidor.'
  } finally {
    enviando.value = false
  }
}
</script>
