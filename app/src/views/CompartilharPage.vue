<template>
  <ion-page>
    <ion-content class="vale">
      <vazio
        v-if="erro"
        titulo="Não deu para salvar esse link"
        :texto="erro"
      >
        <router-link class="botao botao--noite botao--compacto" to="/abas/lugares" replace>Ir para Meus lugares</router-link>
      </vazio>
      <div v-else class="guardando">
        <ion-spinner name="crescent" />
        <p>Guardando o link...</p>
      </div>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { IonContent, IonPage, IonSpinner } from '@ionic/vue'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Vazio from '@/components/Vazio.vue'
import { api, ErroApi } from '@/services/api'
import type { Salvo } from '@/types'

// Destino do menu "Compartilhar" do celular (share_target do manifest).
// Chega como /compartilhar?url=...&text=...&title=...
const route = useRoute()
const router = useRouter()
const erro = ref('')

function parametro(nome: string): string {
  const valor = route.query[nome]
  return typeof valor === 'string' ? valor : ''
}

onMounted(async () => {
  try {
    const salvo = await api<Salvo>('/salvos/', {
      method: 'POST',
      json: { url: parametro('url'), text: parametro('text'), title: parametro('title') },
    })
    await router.replace(`/abas/lugares/salvo/${salvo.id}`)
  } catch (e) {
    erro.value = e instanceof ErroApi ? e.message : 'Sem conexão com o servidor. Tente compartilhar de novo.'
  }
})
</script>

<style scoped>
.guardando {
  margin-top: 35vh;
  text-align: center;
  color: var(--chasque-tinta-suave);
}

.guardando ion-spinner {
  color: var(--chasque-ocre);
  width: 36px;
  height: 36px;
}
</style>
