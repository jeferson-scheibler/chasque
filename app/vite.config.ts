import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// Em desenvolvimento a API fica atras do mesmo endereco do app (/api),
// entao o cookie de sessao e de primeira parte e nao ha CORS no navegador.
const alvoApi = process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8010'
const alvoMapa = process.env.MAPA_PROXY_TARGET ?? 'http://127.0.0.1:8090'
// Endereços públicos (ex.: chasque.177-44-248-30.sslip.io) atrás do nginx da VM.
const hostsPublicos = (process.env.APP_HOSTS ?? '').split(',').map((h) => h.trim()).filter(Boolean)

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    allowedHosts: hostsPublicos,
    proxy: {
      '/api': { target: alvoApi, changeOrigin: false },
      '/tiles': { target: alvoMapa, changeOrigin: true },
    },
  },
  test: {
    environment: 'node',
  },
})
