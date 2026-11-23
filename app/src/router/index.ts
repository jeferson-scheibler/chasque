import { createRouter, createWebHistory } from '@ionic/vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useSessao } from '@/stores/sessao'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/abas/sugestoes' },
  { path: '/entrar', component: () => import('@/views/EntrarPage.vue'), meta: { publica: true } },
  { path: '/cadastro', component: () => import('@/views/CadastroPage.vue'), meta: { publica: true } },
  {
    path: '/abas/',
    component: () => import('@/views/AbasPage.vue'),
    children: [
      { path: '', redirect: '/abas/sugestoes' },
      { path: 'sugestoes', component: () => import('@/views/SugestoesPage.vue') },
      { path: 'registrar', component: () => import('@/views/RegistrarPage.vue') },
      { path: 'lugares', component: () => import('@/views/LugaresPage.vue') },
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
  if (para.meta.publica && sessao.logado) return '/abas/sugestoes'
})

export default router
