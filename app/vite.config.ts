import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// Em desenvolvimento a API fica atras do mesmo endereco do app (/api),
// entao o cookie de sessao e de primeira parte e nao ha CORS no navegador.
const alvoApi = process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8010'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    proxy: {
      '/api': { target: alvoApi, changeOrigin: false },
    },
  },
  test: {
    environment: 'node',
  },
})
