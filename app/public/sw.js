// Service worker do Chasque: torna o app instalável e recebe os avisos (Web Push).
// Não guarda nada em cache de propósito; tudo vem da rede (sem dados pessoais no aparelho).
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (evento) => evento.waitUntil(self.clients.claim()))
self.addEventListener('fetch', () => {})

self.addEventListener('push', (evento) => {
  let aviso = {}
  try {
    aviso = evento.data ? evento.data.json() : {}
  } catch {
    aviso = { corpo: evento.data ? evento.data.text() : '' }
  }
  const url = typeof aviso.url === 'string' && aviso.url.startsWith('/') ? aviso.url : '/abas/sugestoes'
  evento.waitUntil(
    self.registration.showNotification(aviso.titulo || 'Chasque', {
      body: aviso.corpo || '',
      icon: '/icones/icone-192.png',
      badge: '/icones/icone-192.png',
      tag: aviso.tag || 'chasque',
      data: { url },
      lang: 'pt-BR',
    }),
  )
})

self.addEventListener('notificationclick', (evento) => {
  evento.notification.close()
  const url = new URL(evento.notification.data?.url || '/abas/sugestoes', self.location.origin).href
  evento.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((janelas) => {
      for (const janela of janelas) {
        if (janela.url.startsWith(self.location.origin) && 'focus' in janela) {
          janela.navigate(url)
          return janela.focus()
        }
      }
      return self.clients.openWindow(url)
    }),
  )
})
