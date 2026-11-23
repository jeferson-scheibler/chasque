<template>
  <cena-entrada curta voltar="/entrar">
    <form novalidate @submit.prevent="enviar">
      <h1 class="titulo-pagina">Criar conta</h1>
      <campo v-model="nome" rotulo="Nome" autocomplete="name" placeholder="Como quer ser chamado" />
      <campo v-model="email" rotulo="E-mail" type="email" autocomplete="email" inputmode="email" placeholder="voce@exemplo.com" />
      <campo
        v-model="senha"
        rotulo="Senha"
        type="password"
        autocomplete="new-password"
        ajuda="Pelo menos 10 caracteres. Uma frase curta funciona bem."
      />

      <label class="aceite">
        <input v-model="aceitaTermos" type="checkbox" />
        <span>
          Aceito os termos de uso e a política de privacidade. Minhas visitas ficam privadas; os motivos das que eu
          avaliar bem só ajudam a descrever o lugar somados aos de pelo menos 3 pessoas, sem meu nome. Posso
          desligar isso, baixar ou apagar tudo quando quiser.
        </span>
      </label>

      <p v-if="erro" class="mensagem-erro" role="alert">{{ erro }}</p>

      <button class="botao botao--noite" type="submit" :disabled="enviando">
        {{ enviando ? 'Criando conta...' : 'Criar conta' }}
      </button>
      <p class="alternativa">
        Já tem conta?
        <router-link to="/entrar">Entrar</router-link>
      </p>
    </form>
  </cena-entrada>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Campo from '@/components/Campo.vue'
import CenaEntrada from '@/components/CenaEntrada.vue'
import { ErroApi } from '@/services/api'
import { useSessao } from '@/stores/sessao'

const sessao = useSessao()
const router = useRouter()

const nome = ref('')
const email = ref('')
const senha = ref('')
const aceitaTermos = ref(false)
const erro = ref('')
const enviando = ref(false)

async function enviar() {
  erro.value = ''
  if (!nome.value.trim() || !email.value.trim() || !senha.value) {
    erro.value = 'Preencha nome, e-mail e senha.'
    return
  }
  if (!aceitaTermos.value) {
    erro.value = 'Para criar a conta, aceite os termos de uso e a política de privacidade.'
    return
  }
  enviando.value = true
  try {
    await sessao.cadastrar({ nome: nome.value, email: email.value, senha: senha.value, aceita_termos: true })
    await router.replace('/abas/lugares')
  } catch (e) {
    erro.value = e instanceof ErroApi ? e.message : 'Sem conexão com o servidor.'
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

.aceite {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin: 4px 0 20px;
  font-size: 0.875rem;
  line-height: 1.45;
  color: var(--chasque-tinta-suave);
}

.aceite input {
  flex: none;
  width: 22px;
  height: 22px;
  margin: 0;
  accent-color: var(--chasque-ocre);
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
