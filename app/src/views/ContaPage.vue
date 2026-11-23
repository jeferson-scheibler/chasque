<template>
  <ion-page>
    <ion-header>
      <ion-toolbar><ion-title>Conta</ion-title></ion-toolbar>
    </ion-header>
    <ion-content class="ion-padding">
      <div class="formulario" v-if="sessao.usuario">
        <ion-list lines="full">
          <ion-item>
            <ion-input v-model="nome" label="Nome" label-placement="stacked" />
          </ion-item>
          <ion-item>
            <ion-input :value="sessao.usuario.email" label="E-mail" label-placement="stacked" readonly />
          </ion-item>
          <ion-item>
            <ion-input v-model="cidade" label="Cidade base" label-placement="stacked" placeholder="Ex.: Lajeado" />
          </ion-item>
        </ion-list>
        <ion-button expand="block" class="ion-margin-top" :disabled="!alterado || salvando" @click="salvar">
          Salvar
        </ion-button>

        <h2 class="secao">Seus dados</h2>
        <p class="texto-apoio">Seus registros são privados. Você pode baixar tudo que o Chasque guarda sobre você ou apagar a conta.</p>
        <ion-button expand="block" fill="outline" @click="exportar">Baixar meus dados</ion-button>
        <ion-button expand="block" fill="outline" @click="sair">Sair</ion-button>
        <ion-button expand="block" fill="clear" color="danger" @click="confirmarExclusao">Excluir conta</ion-button>
      </div>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import {
  alertController, IonButton, IonContent, IonHeader, IonInput, IonItem, IonList, IonPage, IonTitle,
  IonToolbar, toastController,
} from '@ionic/vue'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, ErroApi } from '@/services/api'
import { useSessao } from '@/stores/sessao'

const sessao = useSessao()
const router = useRouter()

const nome = ref(sessao.usuario?.nome ?? '')
const cidade = ref(sessao.usuario?.cidade_base ?? '')
const salvando = ref(false)
const alterado = computed(() => nome.value !== sessao.usuario?.nome || cidade.value !== sessao.usuario?.cidade_base)

async function avisar(mensagem: string, cor = 'dark') {
  const toast = await toastController.create({ message: mensagem, duration: 2500, color: cor })
  await toast.present()
}

async function salvar() {
  salvando.value = true
  try {
    await sessao.atualizar({ nome: nome.value, cidade_base: cidade.value })
    await avisar('Dados salvos.')
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
    await avisar('Não foi possível exportar agora.', 'danger')
  }
}

async function sair() {
  await sessao.sair()
  await router.replace('/entrar')
}

async function confirmarExclusao() {
  const alerta = await alertController.create({
    header: 'Excluir conta',
    message: 'Isso apaga a conta e todos os seus registros. Não dá para desfazer. Digite sua senha para confirmar.',
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
    await avisar('Conta excluída.')
  } catch (e) {
    await avisar(e instanceof ErroApi ? e.message : 'Não foi possível excluir.', 'danger')
  }
}
</script>

<style scoped>
.secao {
  margin-top: 2rem;
  font-size: 1.1rem;
}
</style>
