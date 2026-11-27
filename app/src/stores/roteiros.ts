import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/services/api'
import type { Roteiro } from '@/types'

/** Roteiros dos próximos fins de semana livres (a agenda precisa estar ligada). */
export const useRoteiros = defineStore('roteiros', () => {
  const lista = ref<Roteiro[]>([])
  const novos = computed(() => lista.value.filter((r) => !r.visto).length)

  async function carregar() {
    try {
      lista.value = await api<Roteiro[]>('/roteiros/')
    } catch {
      // sem rede: fica o que já estava
    }
  }

  function marcarVisto(id: number) {
    const r = lista.value.find((x) => x.id === id)
    if (r) r.visto = true
  }

  function remover(id: number) {
    lista.value = lista.value.filter((x) => x.id !== id)
  }

  return { lista, novos, carregar, marcarVisto, remover }
})

const DIAS = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado']

/** "2026-11-28" vira Date ao meio-dia local, sem escorregar de dia pelo fuso. */
export function dataDoDia(iso: string) {
  const [a, m, d] = iso.split('-').map(Number)
  return new Date(a, m - 1, d, 12)
}

export function nomeDoDia(iso: string) {
  return DIAS[dataDoDia(iso).getDay()]
}

/** "sábado, 28/11", ou "amanhã" quando for o caso. */
export function quandoDoRoteiro(iso: string) {
  const dia = dataDoDia(iso)
  const amanha = new Date()
  amanha.setDate(amanha.getDate() + 1)
  const dm = `${String(dia.getDate()).padStart(2, '0')}/${String(dia.getMonth() + 1).padStart(2, '0')}`
  if (dia.toDateString() === amanha.toDateString()) return `amanhã, ${nomeDoDia(iso)} ${dm}`
  return `${nomeDoDia(iso)}, ${dm}`
}

export function tituloDoRoteiro(r: Roteiro) {
  const dia = nomeDoDia(r.dia)
  const Dia = dia[0].toUpperCase() + dia.slice(1)
  if (r.viagem && r.cidade) return `Bate e volta para ${r.cidade}`
  return r.cidade ? `${Dia} em ${r.cidade}` : `${Dia} livre`
}
