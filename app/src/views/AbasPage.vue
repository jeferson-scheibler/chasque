<template>
  <ion-page>
    <ion-tabs>
      <ion-router-outlet />
      <ion-tab-bar slot="bottom" class="abas">
        <BordaAbas class="abas__borda" />
        <ion-tab-button tab="lugares" href="/abas/lugares">
          <ion-icon :icon="bookmarkOutline" aria-hidden="true" />
          <ion-label>Lugares</ion-label>
        </ion-tab-button>
        <ion-tab-button tab="sugestoes" href="/abas/sugestoes">
          <ion-icon :icon="sparklesOutline" aria-hidden="true" />
          <ion-label>Sugestões</ion-label>
        </ion-tab-button>

        <!-- O sol nasce do meio da barra: é o botão de adicionar. -->
        <div class="abas__vaga">
          <button class="sol" type="button" aria-label="Adicionar lugar" @click="adicionar.abrir()">
            <ion-icon :icon="add" aria-hidden="true" />
          </button>
        </div>

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
    <adicionar-folha />
  </ion-page>
</template>

<script setup lang="ts">
import { IonIcon, IonLabel, IonPage, IonRouterOutlet, IonTabBar, IonTabButton, IonTabs } from '@ionic/vue'
import { add, bookmarkOutline, mapOutline, personCircleOutline, sparklesOutline } from 'ionicons/icons'
import AdicionarFolha from '@/components/AdicionarFolha.vue'
import BordaAbas from '@/components/BordaAbas.vue'
import { useAdicionar } from '@/stores/adicionar'

const adicionar = useAdicionar()
</script>

<style scoped>
.abas {
  /* o Ionic usa contain: strict, que cortaria o sol e a borda ondulada */
  contain: none;
  overflow: visible;
  height: calc(64px + var(--ion-safe-area-bottom, 0px));
  position: relative;
}

/* borda de cima: um trecho da divisa do RS, de cabeça para baixo */
.abas__borda {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% - 1px);
  pointer-events: none;
}

ion-tab-button {
  --color: var(--chasque-faixa-suave);
  --color-selected: var(--chasque-ocre);
  --ripple-color: var(--chasque-ocre);
  background: transparent;
  font-weight: 500;
}

ion-tab-button ion-icon {
  font-size: 23px;
}

ion-tab-button ion-label {
  font-size: 0.72rem;
  letter-spacing: 0.01em;
}

.abas__vaga {
  flex: 0 0 78px;
  align-self: stretch;
  position: relative;
}

.sol {
  position: absolute;
  left: 50%;
  top: -30px;
  width: 64px;
  height: 64px;
  margin-left: -32px;
  border: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--chasque-ocre);
  color: var(--chasque-sobre-ocre);
  /* anel na cor da faixa: o sol "recorta" a barra, como no logo */
  box-shadow:
    0 0 0 6px var(--chasque-faixa),
    0 0 34px 6px var(--chasque-ocre-brilho);
  transition: transform 0.18s cubic-bezier(0.3, 1.4, 0.5, 1), box-shadow 0.25s ease;
}

.sol ion-icon {
  font-size: 32px;
}

.sol:active {
  transform: scale(0.9);
  box-shadow:
    0 0 0 6px var(--chasque-faixa),
    0 0 46px 12px var(--chasque-ocre-brilho);
}
</style>
