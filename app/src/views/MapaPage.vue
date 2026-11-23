<template>
  <em-construcao
    titulo="Mapa"
    :icone="mapOutline"
    descricao="Seus lugares no mapa do Vale do Taquari."
    etapa="Etapa 5: mapa com MapLibre e tiles próprios"
  />
</template>

<script setup lang="ts">
import { mapOutline } from 'ionicons/icons'
import EmConstrucao from '@/components/EmConstrucao.vue'
</script>
