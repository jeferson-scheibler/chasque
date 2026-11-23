import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, guardarTokens, limparSessao, renovar } from '@/services/api'

export interface Usuario {
  id: number
  email: string
  nome: string
  cidade_base: string
  contribuir_motivos: boolean
  date_joined: string
}

interface RespostaLogin {
  access: string
  refresh?: string
  usuario: Usuario
}

export const useSessao = defineStore('sessao', () => {
  const usuario = ref<Usuario | null>(null)
  const restaurada = ref(false)
  const logado = computed(() => usuario.value !== null)

  /** Na abertura do app: se ainda houver sessao valida, recupera o usuario. */
  async function restaurar() {
    if (restaurada.value) return
    try {
      if (await renovar()) usuario.value = await api<Usuario>('/me/')
    } catch {
      usuario.value = null
    } finally {
      restaurada.value = true
    }
  }

  async function entrar(email: string, senha: string) {
    const r = await api<RespostaLogin>('/auth/entrar/', { method: 'POST', json: { email, senha }, semRenovar: true })
    await guardarTokens(r)
    usuario.value = r.usuario
  }

  async function cadastrar(dados: { nome: string; email: string; senha: string; aceita_termos: boolean }) {
    const r = await api<RespostaLogin>('/auth/cadastro/', { method: 'POST', json: dados, semRenovar: true })
    await guardarTokens(r)
    usuario.value = r.usuario
  }

  async function atualizar(dados: Partial<Pick<Usuario, 'nome' | 'cidade_base' | 'contribuir_motivos'>>) {
    usuario.value = await api<Usuario>('/me/', { method: 'PATCH', json: dados })
  }

  async function sair() {
    try {
      await api('/auth/sair/', { method: 'POST', json: {}, semRenovar: true })
    } finally {
      await limparSessao()
      usuario.value = null
    }
  }

  async function excluirConta(senha: string) {
    await api('/me/', { method: 'DELETE', json: { senha } })
    await limparSessao()
    usuario.value = null
  }

  return { usuario, logado, restaurar, entrar, cadastrar, atualizar, sair, excluirConta }
})
