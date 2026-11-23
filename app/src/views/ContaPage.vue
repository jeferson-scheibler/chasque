<template>
  <ion-page>
    <faixa :titulo="sessao.usuario?.nome ?? 'Conta'" :subtitulo="sessao.usuario?.email" :arvores="false">
      <template #acoes>
        <span slot="end" class="iniciais" aria-hidden="true">{{ iniciais }}</span>
      </template>
    </faixa>

    <ion-content class="vale">
      <form v-if="sessao.usuario" class="bloco" novalidate @submit.prevent="salvar">
        <h2 class="secao-titulo">Seu perfil</h2>
        <campo v-model="nome" rotulo="Nome" autocomplete="name" />
        <campo v-model="cidade" rotulo="Cidade onde você mora" placeholder="Lajeado" autocomplete="address-level2" />
        <button v-if="alterado" type="submit" class="botao botao--noite" :disabled="salvando">
          {{ salvando ? 'Salvando...' : 'Salvar perfil' }}
        </button>
      </form>

      <h2 class="secao-titulo">Seus dados</h2>
      <p class="secao-apoio">Seus registros são privados. Você pode levar tudo com você ou apagar a conta.</p>
      <ul class="linhas">
        <li>
          <button type="button" class="linha" @click="exportar">
            <span class="linha__icone"><ion-icon :icon="downloadOutline" aria-hidden="true" /></span>
            <span class="linha__texto">
              <span class="linha__titulo">Baixar meus dados</span>
              <span class="linha__meta">Um arquivo com tudo o que o Chasque guarda sobre você</span>
            </span>
          </button>
        </li>
        <li>
          <button type="button" class="linha" @click="sair">
            <span class="linha__icone"><ion-icon :icon="logOutOutline" aria-hidden="true" /></span>
            <span class="linha__texto">
              <span class="linha__titulo">Sair</span>
              <span class="linha__meta">Encerra a sessão neste aparelho</span>
            </span>
          </button>
        </li>
      </ul>

      <button type="button" class="botao botao--perigo excluir" @click="confirmarExclusao">
        <ion-icon :icon="trashOutline" aria-hidden="true" />Excluir conta
      </button>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { alertController, IonContent, IonIcon, IonPage, toastController } from '@ionic/vue'
import { downloadOutline, logOutOutline, trashOutline } from 'ionicons/icons'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import Campo from '@/components/Campo.vue'
import Faixa from '@/components/Faixa.vue'
import { api, ErroApi } from '@/services/api'
import { useSessao } from '@/stores/sessao'

const sessao = useSessao()
const router = useRouter()

const nome = ref(sessao.usuario?.nome ?? '')
const cidade = ref(sessao.usuario?.cidade_base ?? '')
const salvando = ref(false)
const alterado = computed(() => nome.value !== sessao.usuario?.nome || cidade.value !== sessao.usuario?.cidade_base)
const iniciais = computed(() =>
  (sessao.usuario?.nome ?? '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join(''),
)

async function avisar(mensagem: string, cor?: string) {
  const toast = await toastController.create({ message: mensagem, duration: 2400, color: cor, position: 'top' })
  await toast.present()
}

async function salvar() {
  salvando.value = true
  try {
    await sessao.atualizar({ nome: nome.value, cidade_base: cidade.value })
    await avisar('Perfil salvo')
  } catch (e) {
    await avisar(e instanceof ErroApi ? e.message : 'Não foi possível salvar.', 'danger')
  } finally {
    salvando.value = false
  }
}

async function exportar() {
  try {
    const dados = await api('/me/exportar/')
    // Na web baixa um arquivo. No app nativo isso vai precisar do plugin de arquivos/compartilhar.
    const blob = new Blob([JSON.stringify(dados, null, 2)], { type: 'application/json' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'chasque-meus-dados.json'
    link.click()
    URL.revokeObjectURL(link.href)
  } catch {
    await avisar('Não foi possível baixar agora.', 'danger')
  }
}

async function sair() {
  await sessao.sair()
  await router.replace('/entrar')
}

async function confirmarExclusao() {
  const alerta = await alertController.create({
    header: 'Excluir conta',
    message: 'Isso apaga a conta e tudo o que você salvou. Não dá para desfazer. Digite sua senha para confirmar.',
    inputs: [{ name: 'senha', type: 'password', placeholder: 'Senha', attributes: { autocomplete: 'current-password' } }],
    buttons: [
      { text: 'Cancelar', role: 'cancel' },
      { text: 'Excluir', role: 'destructive', handler: (valores: { senha: string }) => { void excluir(valores.senha) } },
    ],
  })
  await alerta.present()
}

async function excluir(senha: string) {
  try {
    await sessao.excluirConta(senha)
    await router.replace('/entrar')
    await avisar('Conta excluída')
  } catch (e) {
    await avisar(e instanceof ErroApi ? e.message : 'Não foi possível excluir.', 'danger')
  }
}
</script>

<style scoped>
.iniciais {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  margin-right: 6px;
  border-radius: 50%;
  background: var(--chasque-ocre);
  color: var(--chasque-sobre-ocre);
  font-family: var(--chasque-fonte-titulo);
  font-weight: 700;
  font-size: 1.05rem;
}

.bloco {
  padding: 0 20px;
}

.bloco .secao-titulo {
  margin-left: 0;
  margin-right: 0;
  margin-bottom: 14px;
}

.excluir {
  margin: 28px auto 0;
  width: auto;
  padding: 0 18px;
}
</style>
