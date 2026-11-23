<template>
  <ion-page>
    <faixa titulo="Mapa" subtitulo="Rio Grande do Sul" />
    <ion-content class="vale">
      <vazio
        titulo="O mapa dos seus lugares está a caminho"
        texto="Logo você vai ver aqui tudo o que salvou e visitou, e o que fica perto de onde você está."
      />
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { IonContent, IonPage } from '@ionic/vue'
import Faixa from '@/components/Faixa.vue'
import Vazio from '@/components/Vazio.vue'
</script>
