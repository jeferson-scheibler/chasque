<template>
  <ion-page>
    <ion-content class="vale">
      <vazio
        v-if="erro"
        pose="duvida"
        titulo="Não deu para salvar esse link"
        :texto="erro"
      >
        <router-link class="botao botao--noite botao--compacto" to="/abas/lugares" replace>Ir para Meus lugares</router-link>
      </vazio>
      <div v-else class="guardando" role="status">
        <mascote pose="caminho" class="guardando__chasque" />
        <p>Levando o recado...</p>
      </div>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { IonContent, IonPage } from '@ionic/vue'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Mascote from '@/components/Mascote.vue'
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

.guardando__chasque {
  height: 120px;
  width: auto;
  margin: 0 auto 14px;
  animation: passo 0.7s ease-in-out infinite alternate;
}

/* o chasque vai e volta no lugar enquanto o link é guardado */
@keyframes passo {
  from {
    transform: translateY(0) rotate(-2deg);
  }
  to {
    transform: translateY(-4px) rotate(2deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .guardando__chasque {
    animation: none;
  }
}
</style>
