import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@capacitor/core', () => ({ Capacitor: { isNativePlatform: () => false } }))

const { api, definirAccess, ErroApi, mensagemDe } = await import('./api')

function json(status: number, corpo: unknown) {
  return new Response(JSON.stringify(corpo), { status, headers: { 'content-type': 'application/json' } })
}

describe('api', () => {
  beforeEach(() => {
    definirAccess('velho')
    vi.restoreAllMocks()
  })

  it('renova a sessao uma vez no 401 e repete o pedido com o token novo', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(json(401, { detail: 'expirado' }))
      .mockResolvedValueOnce(json(200, { access: 'novo' }))
      .mockResolvedValueOnce(json(200, { nome: 'Ana' }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(api('/me/')).resolves.toEqual({ nome: 'Ana' })

    expect(fetchMock.mock.calls[1][0]).toBe('/api/auth/renovar/')
    const repetido = fetchMock.mock.calls[2][1].headers as Headers
    expect(repetido.get('Authorization')).toBe('Bearer novo')
  })

  it('pedidos simultaneos com 401 compartilham uma unica renovacao', async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url === '/api/auth/renovar/') return json(200, { access: 'novo' })
      return fetchMock.mock.calls.filter(([u]) => u === url).length <= 1 ? json(401, {}) : json(200, { ok: url })
    })
    vi.stubGlobal('fetch', fetchMock)

    await Promise.all([api('/a/'), api('/b/')])
    expect(fetchMock.mock.calls.filter(([u]) => u === '/api/auth/renovar/')).toHaveLength(1)
  })

  it('sem sessao valida, devolve o erro original', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(json(401, { detail: 'Credenciais ausentes.' }))
      .mockResolvedValueOnce(json(401, { detail: 'Sessão expirada.' })))

    const erro: unknown = await api('/me/').catch((e: unknown) => e)
    expect(erro).toBeInstanceOf(ErroApi)
    expect((erro as InstanceType<typeof ErroApi>).status).toBe(401)
  })

  it('transforma erro do DRF em frase', () => {
    expect(mensagemDe({ senha: ['Senha curta.'] })).toBe('Senha curta.')
    expect(mensagemDe({ detail: 'Proibido.' })).toBe('Proibido.')
  })
})
