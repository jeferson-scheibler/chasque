import { IonicVue } from '@ionic/vue'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

import '@ionic/vue/css/core.css'
import '@ionic/vue/css/normalize.css'
import '@ionic/vue/css/structure.css'
import '@ionic/vue/css/typography.css'
import '@ionic/vue/css/padding.css'
import '@ionic/vue/css/flex-utils.css'
import '@ionic/vue/css/text-alignment.css'
import '@ionic/vue/css/display.css'
import '@fontsource-variable/bricolage-grotesque'
import '@fontsource-variable/figtree'
import './theme/variables.css'
import './theme/botoes.css'

const app = createApp(App).use(IonicVue).use(createPinia()).use(router)

router.isReady().then(() => app.mount('#app'))

// O service worker torna o app instalável (PWA), o que habilita o menu Compartilhar no Android.
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  void navigator.serviceWorker.register('/sw.js')
}
