<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start"><ion-back-button default-href="/entrar" text="Voltar" /></ion-buttons>
        <ion-title>Criar conta</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content class="ion-padding">
      <form class="formulario" @submit.prevent="enviar">
        <ion-list lines="full">
          <ion-item>
            <ion-input v-model="nome" label="Nome" label-placement="stacked" autocomplete="name" required />
          </ion-item>
          <ion-item>
            <ion-input v-model="email" label="E-mail" label-placement="stacked" type="email" autocomplete="email" inputmode="email" required />
          </ion-item>
          <ion-item>
            <ion-input
              v-model="senha"
              label="Senha"
              label-placement="stacked"
              type="password"
              autocomplete="new-password"
              helper-text="Pelo menos 10 caracteres."
              required
            >
              <ion-input-password-toggle slot="end" />
            </ion-input>
          </ion-item>
          <ion-item>
            <ion-checkbox v-model="aceitaTermos" label-placement="end" justify="start">
              Li e aceito os termos de uso e a política de privacidade. Meus registros ficam privados por padrão.
            </ion-checkbox>
          </ion-item>
        </ion-list>

        <ion-text v-if="erro" color="danger"><p role="alert">{{ erro }}</p></ion-text>

        <ion-button expand="block" type="submit" class="ion-margin-top" :disabled="enviando || !aceitaTermos">
          {{ enviando ? 'Criando...' : 'Criar conta' }}
        </ion-button>
      </form>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import {
  IonBackButton, IonButton, IonButtons, IonCheckbox, IonContent, IonHeader, IonInput,
  IonInputPasswordToggle, IonItem, IonList, IonPage, IonText, IonTitle, IonToolbar,
} from '@ionic/vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ErroApi } from '@/services/api'
import { useSessao } from '@/stores/sessao'

const sessao = useSessao()
const router = useRouter()

const nome = ref('')
const email = ref('')
const senha = ref('')
const aceitaTermos = ref(false)
const erro = ref('')
const enviando = ref(false)

async function enviar() {
  erro.value = ''
  enviando.value = true
  try {
    await sessao.cadastrar({ nome: nome.value, email: email.value, senha: senha.value, aceita_termos: aceitaTermos.value })
    await router.replace('/abas/sugestoes')
  } catch (e) {
    erro.value = e instanceof ErroApi ? e.message : 'Sem conexão com o servidor.'
  } finally {
    enviando.value = false
  }
}
</script>
