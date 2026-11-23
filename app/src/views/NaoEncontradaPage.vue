<template>
  <ion-page>
    <ion-content class="perdido">
      <div class="perdido__centro">
        <mascote pose="relinchando" class="perdido__chasque" />
        <h1>Esse caminho não leva a lugar nenhum</h1>
        <p>O link pode estar incompleto ou a página saiu do ar. O chasque volta com você para o começo.</p>
        <router-link class="botao botao--sol" to="/" replace>Voltar para o Chasque</router-link>
      </div>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { IonContent, IonPage } from '@ionic/vue'
import Mascote from '@/components/Mascote.vue'
</script>

<style scoped>
.perdido {
  --background: var(--colina-perto);
}

.perdido__centro {
  min-height: 100%;
  max-width: 400px;
  margin: 0 auto;
  padding: calc(var(--ion-safe-area-top, 0px) + 12vh) 28px calc(32px + var(--ion-safe-area-bottom, 0px));
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

/* o chasque entra a trote pela esquerda */
.perdido__chasque {
  width: min(250px, 70vw);
  height: auto;
  margin-bottom: 26px;
  animation: trote 1.1s cubic-bezier(0.25, 0.8, 0.3, 1) both;
}

h1 {
  margin: 0 0 10px;
  font-size: 1.6rem;
  font-weight: 650;
  line-height: 1.15;
  color: var(--chasque-tinta);
}

p {
  margin: 0 0 26px;
  line-height: 1.5;
  color: var(--chasque-tinta-suave);
}

.botao {
  width: auto;
  padding: 0 26px;
}

@keyframes trote {
  from {
    opacity: 0;
    transform: translateX(-40vw);
  }
  60% {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .perdido__chasque {
    animation: none;
  }
}
</style>
