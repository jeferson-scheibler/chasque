import { defineStore } from 'pinia'
import { ref } from 'vue'

/** Abre e fecha a folha "Salvar do Instagram" de qualquer tela (botão do sol, estados vazios). */
export const useAdicionar = defineStore('adicionar', () => {
  const aberto = ref(false)
  return {
    aberto,
    abrir: () => { aberto.value = true },
    fechar: () => { aberto.value = false },
  }
})
