<template>
  <em-construcao
    titulo="Registrar visita"
    :icone="addCircleOutline"
    descricao="Escolha o lugar, toque nos motivos e na ocasião. Três toques e pronto."
    etapa="Etapa 3: registro e lista pessoal"
  />
</template>

<script setup lang="ts">
import { addCircleOutline } from 'ionicons/icons'
import EmConstrucao from '@/components/EmConstrucao.vue'
</script>
