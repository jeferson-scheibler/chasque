<template>
  <ion-modal
    class="folha"
    :is-open="adicionar.aberto"
    :initial-breakpoint="1"
    :breakpoints="[0, 1]"
    handle-behavior="cycle"
    @did-dismiss="aoFechar"
    @did-present="focar"
  >
    <div class="folha__corpo">
      <h2>Adicionar</h2>
      <h3 class="folha__sub">Do Instagram</h3>
      <p class="folha__apoio">Cole o link de um post, reel ou perfil. O Chasque guarda só o link, sem rastreio.</p>

      <form @submit.prevent="salvar">
        <div class="campo" :class="{ 'campo--ok': deteccao.ok, 'campo--erro': mostrarErro }">
          <ion-icon :icon="logoInstagram" aria-hidden="true" class="campo__icone" />
          <input
            ref="entrada"
            v-model="link"
            type="url"
            inputmode="url"
            autocomplete="off"
            autocapitalize="off"
            spellcheck="false"
            placeholder="instagram.com/reel/..."
            aria-label="Link do Instagram"
            @input="tocado = true"
          />
          <button type="button" class="campo__colar" @click="colar">Colar</button>
        </div>

        <p class="aviso" :class="{ 'aviso--ok': deteccao.ok, 'aviso--erro': mostrarErro }" aria-live="polite">
          <template v-if="deteccao.ok">
            <ion-icon :icon="checkmarkCircle" aria-hidden="true" />{{ deteccao.texto }}
          </template>
          <template v-else-if="mostrarErro">
            <ion-icon :icon="alertCircleOutline" aria-hidden="true" />{{ erro || deteccao.texto }}
          </template>
          <template v-else>No Instagram, toque em compartilhar e em "Copiar link".</template>
        </p>

        <button type="submit" class="botao-sol" :disabled="salvando">
          {{ salvando ? 'Salvando...' : 'Salvar link' }}
        </button>
      </form>

      <button type="button" class="folha__depois" @click="registrarVisita">
        <ion-icon :icon="footstepsOutline" aria-hidden="true" />
        <span>
          <strong>Registrar uma visita</strong>
          <span>Guarde por que você gostou de um lugar onde já foi.</span>
        </span>
        <ion-icon :icon="chevronForward" aria-hidden="true" class="folha__seta" />
      </button>
    </div>
  </ion-modal>
</template>

<script setup lang="ts">
import { IonIcon, IonModal } from '@ionic/vue'
import { alertCircleOutline, checkmarkCircle, chevronForward, footstepsOutline, logoInstagram } from 'ionicons/icons'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, ErroApi } from '@/services/api'
import { useAdicionar } from '@/stores/adicionar'
import type { Salvo } from '@/types'

const adicionar = useAdicionar()
const router = useRouter()

const entrada = ref<HTMLInputElement | null>(null)
const link = ref('')
const tocado = ref(false)
const salvando = ref(false)
const erro = ref('')

// Só para dar retorno enquanto a pessoa digita. Quem valida de verdade é a API.
const deteccao = computed(() => {
  const texto = link.value.trim()
  if (!texto) return { ok: false, texto: '' }
  const m = texto.match(/(?:https?:\/\/)?(?:www\.|m\.)?(?:instagram\.com|instagr\.am)\/([^\s?#]+)/i)
  if (!m) return { ok: false, texto: 'Esse link não é do Instagram.' }
  const partes = m[1].split('/').filter(Boolean).map((p) => p.toLowerCase())
  const tipo = partes.find((p) => ['reel', 'reels', 'tv', 'p'].includes(p))
  if (tipo === 'p') return { ok: true, texto: 'Post do Instagram' }
  if (tipo) return { ok: true, texto: 'Reel do Instagram' }
  if (partes[0] === 'stories' && partes[1]) return { ok: true, texto: `Perfil @${partes[1]}` }
  if (partes.length === 1 && /^[a-z0-9._]{1,30}$/.test(partes[0])) return { ok: true, texto: `Perfil @${partes[0]}` }
  return { ok: false, texto: 'Esse link não é de um post, reel ou perfil.' }
})

const mostrarErro = computed(() => Boolean(erro.value) || (tocado.value && !deteccao.value.ok && link.value.trim() !== ''))

function focar() {
  entrada.value?.focus()
}

async function colar() {
  try {
    link.value = (await navigator.clipboard.readText()).trim()
    tocado.value = true
    erro.value = ''
  } catch {
    // Sem permissão para ler a área de transferência: a pessoa cola pelo teclado.
    entrada.value?.focus()
  }
}

async function salvar() {
  tocado.value = true
  erro.value = ''
  if (!link.value.trim()) {
    erro.value = 'Cole o link antes de salvar.'
    return
  }
  salvando.value = true
  try {
    const salvo = await api<Salvo>('/salvos/', { method: 'POST', json: { url: link.value.trim() } })
    adicionar.fechar()
    await router.push(`/abas/lugares/salvo/${salvo.id}`)
  } catch (e) {
    erro.value = e instanceof ErroApi ? e.message : 'Sem conexão com o servidor. Tente de novo.'
  } finally {
    salvando.value = false
  }
}

async function registrarVisita() {
  adicionar.fechar()
  await router.push('/abas/lugares/visita/nova')
}

function aoFechar() {
  adicionar.fechar()
  link.value = ''
  tocado.value = false
  erro.value = ''
}
</script>

<style scoped>
.folha {
  --height: auto;
  --border-radius: 28px;
  --background: var(--chasque-papel);
  --handle-background: var(--chasque-neblina);
}

.folha__corpo {
  padding: 28px 22px calc(24px + var(--ion-safe-area-bottom, 0px));
}

h2 {
  margin: 0 0 6px;
  font-size: 1.5rem;
  font-weight: 650;
  color: var(--chasque-tinta);
}

.folha__sub {
  margin: 0 0 4px;
  font-family: var(--chasque-fonte-titulo);
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--chasque-tinta);
}

.folha__apoio {
  margin: 0 0 20px;
  color: var(--chasque-tinta-suave);
  line-height: 1.45;
}

.campo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 6px 6px 14px;
  border-radius: 16px;
  background: var(--chasque-fundo);
  border: 1.5px solid var(--chasque-neblina);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.campo:focus-within {
  border-color: var(--chasque-faixa);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--chasque-faixa) 12%, transparent);
}

.campo--ok {
  border-color: var(--ion-color-success);
}

.campo--erro {
  border-color: var(--ion-color-danger);
}

.campo__icone {
  font-size: 20px;
  color: var(--chasque-tinta-suave);
  flex: none;
}

.campo input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--chasque-tinta);
  font: inherit;
  font-size: 1rem;
  padding: 10px 0;
}

.campo input::placeholder {
  color: var(--ion-placeholder-color);
}

.campo__colar {
  flex: none;
  border: 0;
  border-radius: 12px;
  padding: 10px 14px;
  background: var(--chasque-faixa);
  color: var(--chasque-faixa-texto);
  font: inherit;
  font-weight: 600;
  font-size: 0.9rem;
}

.campo__colar:active {
  transform: scale(0.96);
}

.aviso {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 22px;
  margin: 10px 2px 18px;
  font-size: 0.875rem;
  color: var(--chasque-tinta-suave);
}

.aviso ion-icon {
  font-size: 18px;
  flex: none;
}

.aviso--ok {
  color: var(--ion-color-success);
}

.aviso--erro {
  color: var(--ion-color-danger);
}

.botao-sol {
  width: 100%;
  height: 54px;
  border: 0;
  border-radius: 16px;
  background: var(--chasque-ocre);
  color: var(--chasque-sobre-ocre);
  font: inherit;
  font-size: 1.05rem;
  font-weight: 700;
  box-shadow: 0 10px 24px -10px var(--chasque-ocre-brilho);
  transition: transform 0.15s ease, filter 0.15s ease;
}

.botao-sol:active {
  transform: scale(0.98);
  filter: brightness(0.95);
}

.botao-sol:disabled {
  opacity: 0.7;
}

.folha__depois {
  display: flex;
  gap: 14px;
  align-items: center;
  width: 100%;
  margin-top: 22px;
  padding: 18px 0 4px;
  border: 0;
  border-top: 1px solid var(--chasque-neblina);
  background: transparent;
  color: var(--chasque-tinta-suave);
  font: inherit;
  text-align: left;
}

.folha__depois > span {
  flex: 1;
}

.folha__seta {
  font-size: 18px !important;
  margin-top: 0 !important;
}

.folha__depois ion-icon {
  font-size: 22px;
  flex: none;
  margin-top: 2px;
}

.folha__depois strong {
  display: block;
  color: var(--chasque-tinta);
  font-weight: 600;
  margin-bottom: 2px;
}

.folha__depois span span {
  font-size: 0.875rem;
  line-height: 1.4;
}
</style>
