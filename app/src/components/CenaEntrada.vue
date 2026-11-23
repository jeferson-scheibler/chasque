<template>
  <ion-page>
    <ion-content :fullscreen="true" class="cena" :scroll-y="true">
      <div class="cena__ceu" :class="{ 'cena__ceu--curta': curta }">
        <ion-button v-if="voltar" class="cena__voltar" fill="clear" :router-link="voltar" router-direction="back" aria-label="Voltar">
          <ion-icon slot="icon-only" :icon="arrowBack" />
        </ion-button>
        <div class="cena__marca">
          <img src="/marca/chasque-horizontal-claro.svg" alt="Chasque" width="186" height="44" />
          <p v-if="!curta">O recado dos lugares que você gostou.</p>
        </div>
        <div class="cena__paisagem"><paisagem variante="cena" /></div>
      </div>
      <div class="cena__vale">
        <slot />
      </div>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { IonButton, IonContent, IonIcon, IonPage } from '@ionic/vue'
import { arrowBack } from 'ionicons/icons'
import Paisagem from './Paisagem.vue'

defineProps<{ curta?: boolean; voltar?: string }>()
</script>

<style scoped>
.cena {
  --background: var(--colina-perto);
}

.cena__ceu {
  position: relative;
  height: min(52vh, 430px);
  min-height: 330px;
  background: var(--chasque-faixa);
  padding-top: var(--ion-safe-area-top, 0px);
  overflow: hidden;
}

.cena__ceu--curta {
  height: min(34vh, 280px);
  min-height: 230px;
}

.cena__voltar {
  position: absolute;
  z-index: 2;
  top: calc(var(--ion-safe-area-top, 0px) + 8px);
  left: 6px;
  --color: var(--chasque-faixa-texto);
}

.cena__marca {
  position: relative;
  z-index: 1;
  padding: 56px 28px 0;
  animation: surgir 0.9s 0.5s ease-out both;
}

.cena__ceu--curta .cena__marca {
  padding-top: 52px;
  text-align: center;
}

.cena__marca img {
  height: 44px;
  width: auto;
  display: block;
}

.cena__ceu--curta .cena__marca img {
  height: 34px;
  margin: 0 auto;
}

.cena__marca p {
  margin: 14px 0 0;
  max-width: 15ch;
  font-family: var(--chasque-fonte-titulo);
  font-size: 1.65rem;
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--chasque-faixa-texto);
}

.cena__paisagem {
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 62%;
}

.cena__vale {
  position: relative;
  padding: 4px 24px calc(32px + var(--ion-safe-area-bottom, 0px));
  max-width: 460px;
  margin: 0 auto;
  animation: surgir 0.7s 0.7s ease-out both;
}

@keyframes surgir {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
</style>
