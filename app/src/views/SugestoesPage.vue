<template>
  <ion-page>
    <faixa titulo="Sugestões" subtitulo="Pelo seu gosto, não pela média" />
    <ion-content class="vale">
      <vazio
        titulo="Suas sugestões nascem do que você guarda"
        texto="Cada lugar que você salva ensina ao Chasque do que você gosta. Comece por um post ou reel que te deu vontade de ir."
      >
        <button class="botao botao--sol botao--compacto" type="button" @click="adicionar.abrir()">
          <ion-icon :icon="logoInstagram" aria-hidden="true" />Salvar do Instagram
        </button>
      </vazio>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { IonContent, IonIcon, IonPage } from '@ionic/vue'
import { logoInstagram } from 'ionicons/icons'
import Faixa from '@/components/Faixa.vue'
import Vazio from '@/components/Vazio.vue'
import { useAdicionar } from '@/stores/adicionar'

const adicionar = useAdicionar()
</script>
