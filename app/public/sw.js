// Service worker mínimo: só torna o Chasque instalável.
// Não guarda nada em cache de propósito; tudo vem da rede (sem dados pessoais no aparelho).
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (evento) => evento.waitUntil(self.clients.claim()))
self.addEventListener('fetch', () => {})
