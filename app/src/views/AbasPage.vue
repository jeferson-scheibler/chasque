<template>
  <ion-page>
    <ion-tabs>
      <ion-router-outlet />
      <ion-tab-bar slot="bottom">
        <ion-tab-button tab="sugestoes" href="/abas/sugestoes">
          <ion-icon :icon="sparklesOutline" aria-hidden="true" />
          <ion-label>Sugestões</ion-label>
        </ion-tab-button>
        <ion-tab-button tab="registrar" href="/abas/registrar">
          <ion-icon :icon="addCircleOutline" aria-hidden="true" />
          <ion-label>Registrar</ion-label>
        </ion-tab-button>
        <ion-tab-button tab="lugares" href="/abas/lugares">
          <ion-icon :icon="bookmarkOutline" aria-hidden="true" />
          <ion-label>Meus lugares</ion-label>
        </ion-tab-button>
        <ion-tab-button tab="mapa" href="/abas/mapa">
          <ion-icon :icon="mapOutline" aria-hidden="true" />
          <ion-label>Mapa</ion-label>
        </ion-tab-button>
        <ion-tab-button tab="conta" href="/abas/conta">
          <ion-icon :icon="personCircleOutline" aria-hidden="true" />
          <ion-label>Conta</ion-label>
        </ion-tab-button>
      </ion-tab-bar>
    </ion-tabs>
  </ion-page>
</template>

<script setup lang="ts">
import { IonIcon, IonLabel, IonPage, IonRouterOutlet, IonTabBar, IonTabButton, IonTabs } from '@ionic/vue'
import { addCircleOutline, bookmarkOutline, mapOutline, personCircleOutline, sparklesOutline } from 'ionicons/icons'
</script>
