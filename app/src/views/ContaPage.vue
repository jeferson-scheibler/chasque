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

      <router-link to="/abas/conta/pessoas" class="pessoas-entrada cartao-rs">
        <span class="linha__icone"><ion-icon :icon="peopleOutline" aria-hidden="true" /></span>
        <span class="linha__texto">
          <span class="linha__titulo">Pessoas de confiança</span>
          <span class="linha__meta">{{ resumoPessoas }}</span>
        </span>
        <span v-if="pedidos" class="pedidos">{{ pedidos }}</span>
        <ion-icon :icon="chevronForward" class="linha__seta" aria-hidden="true" />
      </router-link>

      <router-link to="/abas/conta/agenda" class="pessoas-entrada agenda-entrada cartao-rs">
        <span class="linha__icone"><ion-icon :icon="calendarOutline" aria-hidden="true" /></span>
        <span class="linha__texto">
          <span class="linha__titulo">Agenda e fins de semana</span>
          <span class="linha__meta">{{ resumoAgenda }}</span>
        </span>
        <ion-icon :icon="chevronForward" class="linha__seta" aria-hidden="true" />
      </router-link>

      <h2 class="secao-titulo">Privacidade</h2>
      <label class="contribuir cartao-rs">
        <span>
          <strong>Ajudar a descrever os lugares</strong>
          <small>
            Os motivos das visitas que você avalia bem entram, somados aos de pelo menos 3 pessoas e sem o seu nome,
            na descrição do lugar. Suas visitas continuam privadas.
          </small>
        </span>
        <ion-toggle
          :checked="sessao.usuario?.contribuir_motivos ?? true"
          aria-label="Ajudar a descrever os lugares"
          @ion-change="alternarContribuir($event.detail.checked)"
        />
      </label>

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
import type { EstadoAgenda } from '@/types'
import { alertController, IonContent, IonIcon, IonPage, IonToggle, onIonViewWillEnter, toastController } from '@ionic/vue'
import { calendarOutline, chevronForward, downloadOutline, logOutOutline, peopleOutline, trashOutline } from 'ionicons/icons'
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

const pedidos = ref(0)
const seguindo = ref(0)
const seguidores = ref(0)
const resumoPessoas = computed(() => {
  if (pedidos.value) return `${pedidos.value} ${pedidos.value === 1 ? 'pedido novo' : 'pedidos novos'}`
  if (!seguindo.value && !seguidores.value) return 'Convide quem você confia'
  return `Você segue ${seguindo.value}, ${seguidores.value} seguem você`
})

const resumoAgenda = ref('Roteiros para os sábados e domingos livres')

onIonViewWillEnter(async () => {
  api<EstadoAgenda>('/agenda/')
    .then((a) => {
      if (!a.conectada) resumoAgenda.value = 'Roteiros para os sábados e domingos livres'
      else if (a.erro) resumoAgenda.value = 'A agenda não abriu na última leitura'
      else {
        const n = a.dias_livres.length
        resumoAgenda.value = n ? `Ligada, ${n === 1 ? '1 fim de semana livre' : `${n} fins de semana livres`} por vir` : 'Ligada, fins de semana cheios'
      }
    })
    .catch(() => undefined)
  try {
    const r = await api<{ pedidos: unknown[]; seguindo: unknown[]; seguidores: unknown[] }>('/pessoas/')
    pedidos.value = r.pedidos.length
    seguindo.value = r.seguindo.length
    seguidores.value = r.seguidores.length
  } catch {
    // a entrada continua funcionando sem o resumo
  }
})

async function alternarContribuir(ligado: boolean) {
  try {
    await sessao.atualizar({ contribuir_motivos: ligado })
    await avisar(ligado ? 'Seus motivos voltam a ajudar' : 'Seus motivos saíram da descrição dos lugares')
  } catch {
    await avisar('Não foi possível salvar.', 'danger')
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

.pessoas-entrada.agenda-entrada {
  margin-top: 10px;
}

.pessoas-entrada {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 18px 16px 0;
  padding: 22px 14px 14px 16px;
  color: inherit;
  text-decoration: none;
}

.pedidos {
  flex: none;
  min-width: 24px;
  height: 24px;
  padding: 0 7px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: var(--chasque-ocre);
  color: var(--chasque-sobre-ocre);
  font-size: 0.8rem;
  font-weight: 700;
}

.contribuir {
  display: flex;
  gap: 16px;
  align-items: center;
  margin: 4px 20px 0;
  padding: 22px 16px 14px;
}

.contribuir strong {
  display: block;
  font-family: var(--chasque-fonte-titulo);
  font-weight: 600;
  color: var(--chasque-tinta);
}

.contribuir small {
  display: block;
  margin-top: 4px;
  font-size: 0.82rem;
  line-height: 1.4;
  color: var(--chasque-tinta-suave);
}

.contribuir ion-toggle {
  flex: none;
  --track-background-checked: var(--chasque-ocre);
  --handle-background-checked: var(--chasque-papel);
}

.excluir {
  margin: 28px auto 0;
  width: auto;
  padding: 0 18px;
}
</style>
