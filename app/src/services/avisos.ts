import { api } from '@/services/api'

/** Avisos no celular (Web Push). No iPhone, só funciona com o Chasque instalado na tela de início. */

export function avisosSuportados() {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

function chaveEmBytes(chave: string) {
  const base64 = (chave + '='.repeat((4 - (chave.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/')
  const bruto = atob(base64)
  return Uint8Array.from(bruto, (c) => c.charCodeAt(0))
}

async function registro() {
  return (await navigator.serviceWorker.getRegistration('/')) ?? navigator.serviceWorker.register('/sw.js')
}

/** A inscrição deste aparelho, se houver. */
export async function inscricaoAtual() {
  if (!avisosSuportados()) return null
  const reg = await navigator.serviceWorker.getRegistration('/')
  return (await reg?.pushManager.getSubscription()) ?? null
}

export class AvisosIndisponiveis extends Error {}

export async function ligarAvisos() {
  if (!avisosSuportados()) throw new AvisosIndisponiveis('Este navegador não recebe avisos. No iPhone, instale o Chasque na tela de início primeiro.')
  const { chave } = await api<{ chave: string }>('/avisos/')
  if (!chave) throw new AvisosIndisponiveis('Os avisos ainda não foram configurados no servidor.')
  const permissao = await Notification.requestPermission()
  if (permissao !== 'granted') throw new AvisosIndisponiveis('O celular não deu permissão para avisos. Libere nas configurações do navegador.')
  const reg = await registro()
  await navigator.serviceWorker.ready
  const inscricao =
    (await reg.pushManager.getSubscription()) ??
    (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: chaveEmBytes(chave) }))
  const dados = inscricao.toJSON()
  await api('/avisos/', {
    method: 'POST',
    json: { endpoint: dados.endpoint, p256dh: dados.keys?.p256dh, auth: dados.keys?.auth },
  })
}

export async function desligarAvisos() {
  const inscricao = await inscricaoAtual()
  if (!inscricao) return
  await api('/avisos/', { method: 'DELETE', json: { endpoint: inscricao.endpoint } }).catch(() => undefined)
  await inscricao.unsubscribe()
}
