/**
 * Cliente HTTP do Chasque.
 *
 * Access token: so em memoria (some ao fechar o app; nunca vai para localStorage).
 * Refresh token:
 *   web    -> cookie httpOnly gravado pela API; o JavaScript nao ve.
 *   nativo -> devolvido no corpo e guardado pelo `cofre` (armazenamento seguro do aparelho).
 *
 * Quando a API responde 401, o cliente renova a sessao uma vez e repete o pedido.
 */
import { Capacitor } from '@capacitor/core'
import { cofre } from './cofre'

export class ErroApi extends Error {
  constructor(
    public status: number,
    public dados: unknown,
  ) {
    super(mensagemDe(dados) ?? `Erro ${status}`)
  }
}

const nativo = Capacitor.isNativePlatform()
const base = nativo ? (import.meta.env.VITE_API_URL ?? '') : ''

let access: string | null = null
let renovando: Promise<boolean> | null = null

export function definirAccess(token: string | null) {
  access = token
}

function cabecalhos(extra?: HeadersInit): Headers {
  const h = new Headers(extra)
  h.set('Accept', 'application/json')
  if (nativo) h.set('X-Chasque-Cliente', 'mobile')
  if (access) h.set('Authorization', `Bearer ${access}`)
  return h
}

async function ler(resposta: Response): Promise<unknown> {
  if (resposta.status === 204) return null
  const tipo = resposta.headers.get('content-type') ?? ''
  return tipo.includes('application/json') ? resposta.json() : resposta.text()
}

/** Guarda os tokens que vierem numa resposta de login, cadastro ou renovacao. */
export async function guardarTokens(dados: { access?: string; refresh?: string }) {
  if (dados.access) access = dados.access
  if (nativo && dados.refresh) await cofre.gravar(dados.refresh)
}

export async function limparSessao() {
  access = null
  if (nativo) await cofre.apagar()
}

/** Tenta renovar a sessao. Pedidos simultaneos compartilham a mesma tentativa. */
export function renovar(): Promise<boolean> {
  renovando ??= (async () => {
    try {
      const corpo = nativo ? { refresh: await cofre.ler() } : {}
      if (nativo && !corpo.refresh) return false
      const r = await fetch(`${base}/api/auth/renovar/`, {
        method: 'POST',
        credentials: 'include',
        headers: cabecalhos({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(corpo),
      })
      if (!r.ok) {
        await limparSessao()
        return false
      }
      await guardarTokens((await r.json()) as { access: string; refresh?: string })
      return true
    } catch {
      return false
    } finally {
      renovando = null
    }
  })()
  return renovando
}

type Opcoes = Omit<RequestInit, 'body'> & { json?: unknown; semRenovar?: boolean }

export async function api<T = unknown>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const { json, semRenovar, headers, ...resto } = opcoes
  const fazer = () =>
    fetch(`${base}/api${caminho}`, {
      credentials: 'include',
      ...resto,
      headers: cabecalhos(json === undefined ? headers : { ...headers, 'Content-Type': 'application/json' }),
      body: json === undefined ? undefined : JSON.stringify(json),
    })

  let resposta = await fazer()
  if (resposta.status === 401 && !semRenovar && (await renovar())) {
    resposta = await fazer()
  }
  const dados = await ler(resposta)
  if (!resposta.ok) throw new ErroApi(resposta.status, dados)
  return dados as T
}

/** Transforma o erro do DRF ({campo: [mensagens]} ou {detail}) em uma frase. */
export function mensagemDe(dados: unknown): string | undefined {
  if (!dados || typeof dados !== 'object') return undefined
  const obj = dados as Record<string, unknown>
  if (typeof obj.detail === 'string') return obj.detail
  for (const valor of Object.values(obj)) {
    if (Array.isArray(valor) && typeof valor[0] === 'string') return valor[0]
    if (typeof valor === 'string') return valor
  }
  return undefined
}
