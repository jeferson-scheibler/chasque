/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Endereco da API no app nativo, ex.: https://api.chasque.app. Na web fica vazio (usa /api). */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}
