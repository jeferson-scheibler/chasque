<template>
  <cena-entrada>
    <form novalidate @submit.prevent="enviar">
      <h1 class="titulo-pagina">Entrar</h1>
      <campo v-model="email" rotulo="E-mail" type="email" autocomplete="email" inputmode="email" placeholder="voce@exemplo.com" />
      <campo v-model="senha" rotulo="Senha" type="password" autocomplete="current-password" />

      <p v-if="erro" class="mensagem-erro" role="alert">{{ erro }}</p>

      <button class="botao botao--noite" type="submit" :disabled="enviando">
        {{ enviando ? 'Entrando...' : 'Entrar' }}
      </button>
      <p class="alternativa">
        Ainda não tem conta?
        <router-link to="/cadastro">Criar conta</router-link>
      </p>
    </form>
  </cena-entrada>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Campo from '@/components/Campo.vue'
import CenaEntrada from '@/components/CenaEntrada.vue'
import { ErroApi } from '@/services/api'
import { useSessao } from '@/stores/sessao'

const sessao = useSessao()
const router = useRouter()
const route = useRoute()

const email = ref('')
const senha = ref('')
const erro = ref('')
const enviando = ref(false)

async function enviar() {
  erro.value = ''
  if (!email.value.trim() || !senha.value) {
    erro.value = 'Preencha o e-mail e a senha.'
    return
  }
  enviando.value = true
  try {
    await sessao.entrar(email.value, senha.value)
    const volta = route.query.volta
    const destino = typeof volta === 'string' && volta.startsWith('/') && !volta.startsWith('//') ? volta : '/abas/lugares'
    await router.replace(destino)
  } catch (e) {
    erro.value = e instanceof ErroApi && e.status === 429
      ? 'Muitas tentativas. Espere um minuto e tente de novo.'
      : e instanceof ErroApi ? e.message : 'Sem conexão com o servidor.'
  } finally {
    enviando.value = false
  }
}
</script>

<style scoped>
.titulo-pagina {
  margin: 0 0 18px;
  font-size: 1.6rem;
  font-weight: 650;
  color: var(--chasque-tinta);
}

.alternativa {
  margin: 18px 0 0;
  text-align: center;
  color: var(--chasque-tinta-suave);
}

.alternativa a {
  color: var(--chasque-tinta);
  font-weight: 650;
  text-decoration-color: var(--chasque-ocre);
  text-decoration-thickness: 2px;
  text-underline-offset: 4px;
}
</style>
