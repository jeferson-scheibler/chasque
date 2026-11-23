import { createRouter, createWebHistory } from '@ionic/vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useSessao } from '@/stores/sessao'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/abas/lugares' },
  { path: '/entrar', component: () => import('@/views/EntrarPage.vue'), meta: { publica: true } },
  { path: '/cadastro', component: () => import('@/views/CadastroPage.vue'), meta: { publica: true } },
  // Destino do menu Compartilhar (manifest share_target). Exige login; o guard guarda a query em ?volta.
  { path: '/compartilhar', component: () => import('@/views/CompartilharPage.vue') },
  {
    path: '/abas/',
    component: () => import('@/views/AbasPage.vue'),
    children: [
      { path: '', redirect: '/abas/lugares' },
      { path: 'sugestoes', component: () => import('@/views/SugestoesPage.vue') },
      { path: 'registrar', redirect: '/abas/lugares' },
      { path: 'lugares', component: () => import('@/views/LugaresPage.vue') },
      { path: 'lugares/salvo/:id(\\d+)', component: () => import('@/views/SalvoPage.vue') },
      { path: 'mapa', component: () => import('@/views/MapaPage.vue') },
      { path: 'conta', component: () => import('@/views/ContaPage.vue') },
    ],
  },
  { path: '/:caminho(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach(async (para) => {
  const sessao = useSessao()
  await sessao.restaurar()
  if (!para.meta.publica && !sessao.logado) {
    return { path: '/entrar', query: para.fullPath !== '/' ? { volta: para.fullPath } : {} }
  }
  if (para.meta.publica && sessao.logado) return '/abas/lugares'
})

export default router
