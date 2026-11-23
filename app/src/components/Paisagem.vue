<template>
  <!--
    A paisagem do logo em tamanho grande: céu, sol ocre e três morros.
    "cena" anima uma vez (o sol nasce atrás dos morros); "vinheta" é a versão parada dos estados vazios.
  -->
  <svg
    class="paisagem"
    :class="[`paisagem--${variante}`]"
    viewBox="0 0 390 240"
    preserveAspectRatio="xMidYMax slice"
    aria-hidden="true"
  >
    <defs>
      <radialGradient :id="idBrilho">
        <stop offset="0%" stop-color="var(--chasque-ocre)" stop-opacity="0.55" />
        <stop offset="100%" stop-color="var(--chasque-ocre)" stop-opacity="0" />
      </radialGradient>
    </defs>
    <g class="paisagem__sol">
      <circle cx="270" cy="120" r="92" :fill="`url(#${idBrilho})`" />
      <circle cx="270" cy="120" r="34" fill="var(--chasque-ocre)" />
    </g>
    <path class="paisagem__longe" d="M0 142C52 124 98 132 152 118C214 101 284 106 390 84V240H0Z" />
    <path class="paisagem__meio" d="M0 178C66 150 122 170 192 155C258 140 318 146 390 126V240H0Z" />
    <path class="paisagem__perto" d="M0 214C76 190 148 214 228 199C298 186 342 196 390 182V240H0Z" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ variante?: 'cena' | 'vinheta' }>(), { variante: 'vinheta' })
// id único por instância: o gradiente não pode colidir quando há duas paisagens na tela
const idBrilho = `brilho-${Math.random().toString(36).slice(2, 8)}`
</script>

<style scoped>
.paisagem {
  display: block;
  width: 100%;
  height: 100%;
}

.paisagem__longe {
  fill: var(--colina-longe);
}
.paisagem__meio {
  fill: var(--colina-meio);
}
.paisagem__perto {
  fill: var(--colina-perto);
}

/* vinheta: tons do vale, sem céu */
.paisagem--vinheta .paisagem__longe {
  fill: var(--chasque-neblina);
}
.paisagem--vinheta .paisagem__meio {
  fill: var(--chasque-faixa);
  opacity: 0.18;
}
.paisagem--vinheta .paisagem__perto {
  fill: var(--chasque-faixa);
}

/* O único movimento automático do app: o sol nasce, os morros assentam. */
.paisagem--cena .paisagem__sol {
  animation: nascer 1.6s cubic-bezier(0.16, 0.8, 0.24, 1) both;
}
.paisagem--cena .paisagem__longe {
  animation: assentar 1.1s 0.05s cubic-bezier(0.2, 0.8, 0.2, 1) both;
}
.paisagem--cena .paisagem__meio {
  animation: assentar 1.1s 0.15s cubic-bezier(0.2, 0.8, 0.2, 1) both;
}
.paisagem--cena .paisagem__perto {
  animation: assentar 1.1s 0.25s cubic-bezier(0.2, 0.8, 0.2, 1) both;
}

@keyframes nascer {
  from {
    transform: translateY(90px);
  }
  to {
    transform: translateY(0);
  }
}

@keyframes assentar {
  from {
    transform: translateY(28px);
  }
  to {
    transform: translateY(0);
  }
}
</style>
