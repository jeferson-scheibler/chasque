import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { nomeDaTag } from '@/categorias'
import { api } from '@/services/api'
import type { Motivo } from '@/types'

/** Os motivos (tags) que dá para marcar numa visita. Carrega uma vez por sessão. */
export const useMotivos = defineStore('motivos', () => {
  const lista = ref<Motivo[]>([])
  let carregando: Promise<void> | null = null

  const porSlug = computed(() => new Map(lista.value.map((m) => [m.slug, m])))
  const grupos = computed(() => {
    const mapa = new Map<string, { nome: string; motivos: Motivo[] }>()
    for (const m of lista.value) {
      if (!mapa.has(m.grupo)) mapa.set(m.grupo, { nome: m.grupo_nome, motivos: [] })
      mapa.get(m.grupo)!.motivos.push(m)
    }
    return [...mapa.values()]
  })

  function carregar() {
    carregando ??= api<Motivo[]>('/tags/')
      .then((r) => { lista.value = r })
      .catch(() => { carregando = null })
    return carregando
  }

  function nome(slug: string) {
    return porSlug.value.get(slug)?.nome ?? nomeDaTag(slug)
  }

  return { lista, grupos, carregar, nome }
})
