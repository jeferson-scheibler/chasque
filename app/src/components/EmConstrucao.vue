<template>
  <ion-page>
    <ion-header>
      <ion-toolbar><ion-title>{{ titulo }}</ion-title></ion-toolbar>
    </ion-header>
    <ion-content class="ion-padding">
      <div class="vazio">
        <ion-icon :icon="icone" aria-hidden="true" />
        <h2>{{ titulo }}</h2>
        <p>{{ descricao }}</p>
        <ion-note>{{ etapa }}</ion-note>
      </div>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { IonContent, IonHeader, IonIcon, IonNote, IonPage, IonTitle, IonToolbar } from '@ionic/vue'

defineProps<{ titulo: string; descricao: string; etapa: string; icone: string }>()
</script>

<style scoped>
.vazio {
  max-width: 360px;
  margin: 15vh auto 0;
  text-align: center;
}
.vazio ion-icon {
  font-size: 56px;
  color: var(--ion-color-primary);
}
.vazio p {
  color: var(--ion-color-medium);
}
</style>
