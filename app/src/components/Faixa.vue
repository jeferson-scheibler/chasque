<template>
  <ion-header class="faixa">
    <ion-toolbar>
      <ion-buttons v-if="voltar" slot="start">
        <ion-back-button :default-href="voltar" text="" aria-label="Voltar" />
      </ion-buttons>
      <div class="faixa__titulos" :class="{ 'faixa__titulos--voltar': voltar, 'faixa__titulos--arvores': arvores }">
        <h1>{{ titulo }}</h1>
        <p v-if="subtitulo">{{ subtitulo }}</p>
      </div>
      <slot name="acoes" />
    </ion-toolbar>
    <div v-if="$slots.default" class="faixa__extra"><slot /></div>
    <!-- borda de baixo: um trecho da divisa norte do RS, com araucárias -->
    <BordaRS class="faixa__borda" :arvores="arvores" />
  </ion-header>
</template>

<script setup lang="ts">
import { IonBackButton, IonButtons, IonHeader, IonToolbar } from '@ionic/vue'
import BordaRS from './BordaRS.vue'

withDefaults(defineProps<{ titulo: string; subtitulo?: string; voltar?: string; arvores?: boolean }>(), {
  arvores: true,
})
</script>

<style scoped>
.faixa {
  position: relative;
  z-index: 2;
}

ion-toolbar {
  --min-height: 68px;
  --padding-start: 20px;
  --padding-end: 12px;
  --padding-top: 6px;
  --padding-bottom: 6px;
}

.faixa__titulos {
  padding: 4px 0;
  min-width: 0;
}

.faixa__titulos--voltar {
  padding-left: 0;
}

.faixa__titulos h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 650;
  line-height: 1.1;
  color: var(--chasque-faixa-texto);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.faixa__titulos p {
  margin: 4px 0 0;
  font-size: 0.9rem;
  color: var(--chasque-faixa-suave);
}

.faixa__extra {
  background: var(--chasque-faixa);
  padding: 2px 16px 10px;
}

.faixa__borda {
  position: absolute;
  left: 0;
  top: calc(100% - 1px);
  pointer-events: none;
  /* acima do ion-toolbar (z-index 10), senão as copas das araucárias ficam escondidas */
  z-index: 11;
}

/* espaço para as araucárias que sobem da borda no canto direito */
.faixa__titulos--arvores {
  padding-right: 96px;
}

/* celular estreito: título e subtítulo um pouco menores, para o subtítulo não quebrar sob as araucárias */
@media (max-width: 359px) {
  ion-toolbar {
    --padding-start: 16px;
  }

  .faixa__titulos h1 {
    font-size: 1.6rem;
  }

  .faixa__titulos p {
    font-size: 0.82rem;
  }

  .faixa__titulos--arvores {
    padding-right: 88px;
  }
}

ion-back-button {
  --color: var(--chasque-faixa-texto);
  --icon-font-size: 24px;
}
</style>
