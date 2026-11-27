<template>
  <ion-page>
    <faixa titulo="Agenda" subtitulo="Fins de semana livres" voltar="/abas/conta" />

    <ion-content class="vale">
      <div v-if="carregando" class="ion-padding ion-text-center"><ion-spinner name="crescent" /></div>

      <template v-else>
        <section v-if="!agenda.conectada || trocando" class="ligar">
          <div class="ligar__cena" aria-hidden="true">
            <ilustracao nome="araucaria" class="ligar__ilustracao" />
          </div>
          <h2 class="ligar__titulo">Fim de semana livre vira passeio</h2>
          <p class="ligar__texto">
            Ligue a sua agenda e o Chasque avisa quando um sábado ou domingo estiver livre, com um roteiro feito dos
            lugares que você salvou.
          </p>

          <form class="ligar__form" @submit.prevent="ligar">
            <label class="ligar__rotulo" for="endereco">Endereço secreto da agenda (iCal)</label>
            <div class="ligar__campo" :class="{ 'ligar__campo--erro': erro }">
              <ion-icon :icon="calendarOutline" aria-hidden="true" />
              <input
                id="endereco"
                v-model="endereco"
                type="url"
                inputmode="url"
                autocomplete="off"
                spellcheck="false"
                placeholder="https://calendar.google.com/...basic.ics"
                :aria-invalid="!!erro"
                aria-describedby="endereco-erro"
              />
            </div>
            <p id="endereco-erro" class="ligar__erro" aria-live="polite">{{ erro }}</p>
            <button type="submit" class="botao botao--sol" :disabled="!endereco.trim() || enviando">
              <ion-spinner v-if="enviando" name="crescent" />
              {{ enviando ? 'Lendo a agenda...' : 'Ligar agenda' }}
            </button>
            <button v-if="trocando" type="button" class="botao botao--texto" @click="trocando = false">Cancelar</button>
          </form>

          <h3 class="secao-titulo">Onde achar o endereço</h3>
          <div class="guias">
            <details v-for="g in GUIAS" :key="g.nome" class="guia">
              <summary>
                <span class="guia__nome">{{ g.nome }}</span>
                <ion-icon :icon="chevronDown" class="guia__seta" aria-hidden="true" />
              </summary>
              <ol>
                <li v-for="passo in g.passos" :key="passo">{{ passo }}</li>
              </ol>
            </details>
          </div>
          <p class="privacidade">
            <ion-icon :icon="lockClosedOutline" aria-hidden="true" />
            O Chasque lê só os horários ocupados. Títulos, locais e convidados dos eventos não são guardados, e o
            endereço não aparece de novo no app.
          </p>
        </section>

        <template v-else>
          <section class="ligada">
            <div class="ligada__cabeca">
              <span class="ligada__icone"><ion-icon :icon="calendarOutline" aria-hidden="true" /></span>
              <span class="linha__texto">
                <span class="linha__titulo">Agenda ligada</span>
                <span class="linha__meta">{{ agenda.servico }}{{ agenda.lida_em ? `, lida ${haQuanto(agenda.lida_em)}` : '' }}</span>
              </span>
            </div>
            <p v-if="agenda.erro" class="ligada__erro">{{ agenda.erro }}</p>

            <h3 class="ligada__sub">Próximos fins de semana</h3>
            <ul class="semanas">
              <li v-for="fds in finsDeSemana" :key="fds.sabado" :class="{ livre: fds.livre }">
                <router-link v-if="fds.roteiro" :to="`/abas/sugestoes/roteiro/${fds.roteiro.id}`" class="semana">
                  <span class="semana__datas">{{ fds.rotulo }}</span>
                  <span class="semana__estado">{{ maiuscula(nomeDoDia(fds.livre!)) }} livre, ver roteiro</span>
                </router-link>
                <div v-else class="semana">
                  <span class="semana__datas">{{ fds.rotulo }}</span>
                  <span class="semana__estado">{{ fds.livre ? `${maiuscula(nomeDoDia(fds.livre))} livre, faltam lugares salvos por perto` : 'Agenda cheia' }}</span>
                </div>
              </li>
            </ul>

            <div class="ligada__acoes">
              <button type="button" class="botao botao--leve botao--compacto" :disabled="lendo" @click="lerAgora">
                <ion-icon :icon="refreshOutline" aria-hidden="true" :class="{ girando: lendo }" />Ler agora
              </button>
              <button type="button" class="botao botao--leve botao--compacto" @click="trocar">Trocar endereço</button>
            </div>
          </section>

          <h2 class="secao-titulo">Avisos no celular</h2>
          <label class="avisos">
            <span>
              <strong>Avisar dos roteiros</strong>
              <small>{{ textoDosAvisos }}</small>
            </span>
            <ion-toggle
              :checked="avisosLigados"
              :disabled="!suportado || mexendoAvisos"
              aria-label="Avisar dos roteiros"
              @ion-change="alternarAvisos($event.detail.checked)"
            />
          </label>
          <button v-if="avisosLigados" type="button" class="botao botao--texto teste" @click="testar">
            Mandar um aviso de teste
          </button>

          <button type="button" class="botao botao--perigo desligar" @click="confirmarDesligar">
            Desligar agenda
          </button>
        </template>
      </template>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { alertController, IonContent, IonIcon, IonPage, IonSpinner, IonToggle, toastController } from '@ionic/vue'
import { calendarOutline, chevronDown, lockClosedOutline, refreshOutline } from 'ionicons/icons'
import { computed, onMounted, ref } from 'vue'
import Faixa from '@/components/Faixa.vue'
import Ilustracao from '@/components/Ilustracao.vue'
import { api, ErroApi } from '@/services/api'
import { avisosSuportados, desligarAvisos, inscricaoAtual, ligarAvisos } from '@/services/avisos'
import { dataDoDia, nomeDoDia, useRoteiros } from '@/stores/roteiros'
import type { EstadoAgenda } from '@/types'

const GUIAS = [
  {
    nome: 'Google Agenda',
    passos: [
      'No computador, abra calendar.google.com e entre em Configurações (a engrenagem).',
      'Em "Configurações das minhas agendas", escolha a sua agenda.',
      'Em "Integrar agenda", copie o "Endereço secreto no formato iCal".',
    ],
  },
  {
    nome: 'Outlook',
    passos: [
      'Em outlook.com, abra Configurações, Calendário, Calendários compartilhados.',
      'Em "Publicar um calendário", escolha a agenda e "Pode ver quando estou ocupado".',
      'Toque em Publicar e copie o link ICS.',
    ],
  },
  {
    nome: 'iPhone (iCloud)',
    passos: [
      'No app Calendário, toque em Calendários e no "i" da agenda.',
      'Ligue "Calendário Público" e toque em Compartilhar Link para copiar.',
      'Quem tiver esse link vê a agenda: guarde só aqui.',
    ],
  },
]

const roteiros = useRoteiros()
const agenda = ref<EstadoAgenda>({ conectada: false })
const carregando = ref(true)
const trocando = ref(false)
const endereco = ref('')
const erro = ref('')
const enviando = ref(false)
const lendo = ref(false)
const suportado = avisosSuportados()
const avisosLigados = ref(false)
const mexendoAvisos = ref(false)

const textoDosAvisos = computed(() => {
  if (!suportado) return 'Este navegador não recebe avisos. No iPhone, instale o Chasque na tela de início primeiro.'
  return avisosLigados.value
    ? 'Ligado neste aparelho. O aviso chega de quarta a sexta, de dia, quando houver um fim de semana livre.'
    : 'Receba no celular o roteiro do fim de semana livre. O roteiro também aparece em Sugestões.'
})

const curta = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit' })

// os três próximos fins de semana, marcando o dia livre (e o roteiro dele, se houver)
const finsDeSemana = computed(() => {
  if (!agenda.value.conectada) return []
  const livres = agenda.value.dias_livres
  const hoje = new Date()
  const sabado = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() + ((6 - hoje.getDay() + 7) % 7), 12)
  return [0, 1, 2].map((i) => {
    const s = new Date(sabado)
    s.setDate(s.getDate() + i * 7)
    const d = new Date(s)
    d.setDate(d.getDate() + 1)
    const livre = livres.find((iso) => {
      const dia = dataDoDia(iso).toDateString()
      return dia === s.toDateString() || dia === d.toDateString()
    })
    return {
      sabado: s.toISOString(),
      rotulo: `${curta.format(s)} e ${curta.format(d)}`,
      livre,
      roteiro: livre ? roteiros.lista.find((r) => r.dia === livre) : undefined,
    }
  })
})

function maiuscula(texto: string) {
  return texto[0].toUpperCase() + texto.slice(1)
}

function haQuanto(iso: string) {
  const minutos = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutos < 2) return 'agora'
  if (minutos < 60) return `há ${minutos} min`
  const horas = Math.round(minutos / 60)
  return horas < 24 ? `há ${horas} h` : `há ${Math.round(horas / 24)} dias`
}

async function avisar(mensagem: string, cor?: string) {
  const toast = await toastController.create({ message: mensagem, duration: 2600, color: cor, position: 'top' })
  await toast.present()
}

async function carregar() {
  try {
    agenda.value = await api<EstadoAgenda>('/agenda/')
    await roteiros.carregar()
    avisosLigados.value = !!(await inscricaoAtual())
  } finally {
    carregando.value = false
  }
}

async function ligar() {
  erro.value = ''
  enviando.value = true
  try {
    agenda.value = await api<EstadoAgenda>('/agenda/', { method: 'PUT', json: { url: endereco.value.trim() } })
    endereco.value = ''
    trocando.value = false
    await roteiros.carregar()
    const livres = agenda.value.conectada ? agenda.value.dias_livres.length : 0
    await avisar(livres ? `Agenda ligada. ${livres === 1 ? '1 fim de semana livre' : `${livres} fins de semana livres`} por vir` : 'Agenda ligada')
  } catch (e) {
    erro.value = e instanceof ErroApi ? e.message : 'Sem conexão com o servidor. Tente de novo.'
  } finally {
    enviando.value = false
  }
}

async function lerAgora() {
  lendo.value = true
  try {
    agenda.value = await api<EstadoAgenda>('/agenda/ler/', { method: 'POST' })
    await roteiros.carregar()
  } catch (e) {
    await avisar(e instanceof ErroApi ? e.message : 'Não foi possível ler a agenda.', 'danger')
  } finally {
    lendo.value = false
  }
}

function trocar() {
  erro.value = ''
  trocando.value = true
}

async function alternarAvisos(ligado: boolean) {
  if (ligado === avisosLigados.value) return
  mexendoAvisos.value = true
  try {
    if (ligado) {
      await ligarAvisos()
      await avisar('Avisos ligados neste aparelho')
    } else {
      await desligarAvisos()
    }
    avisosLigados.value = ligado
  } catch (e) {
    avisosLigados.value = !!(await inscricaoAtual())
    await avisar(e instanceof Error ? e.message : 'Não foi possível mudar os avisos.', 'danger')
  } finally {
    mexendoAvisos.value = false
  }
}

async function testar() {
  try {
    const r = await api<{ enviados: number }>('/avisos/teste/', { method: 'POST' })
    await avisar(r.enviados ? 'Aviso enviado. Deve chegar em instantes' : 'Nenhum aparelho recebeu. Desligue e ligue os avisos de novo')
  } catch (e) {
    await avisar(e instanceof ErroApi ? e.message : 'Não foi possível mandar o aviso.', 'danger')
  }
}

async function confirmarDesligar() {
  const alerta = await alertController.create({
    header: 'Desligar a agenda?',
    message: 'O Chasque esquece o endereço e apaga os roteiros dos próximos fins de semana.',
    buttons: [
      { text: 'Cancelar', role: 'cancel' },
      { text: 'Desligar', role: 'destructive', handler: () => { void desligar() } },
    ],
  })
  await alerta.present()
}

async function desligar() {
  try {
    await api('/agenda/', { method: 'DELETE' })
    agenda.value = { conectada: false }
    await roteiros.carregar()
    await avisar('Agenda desligada')
  } catch {
    await avisar('Não foi possível desligar.', 'danger')
  }
}

onMounted(carregar)
</script>

<style scoped>
.ligar {
  padding: 8px 0 24px;
}

/* a serra com a araucária: o fim de semana que a agenda vai achar */
.ligar__cena {
  max-width: 220px;
  margin: 12px auto 14px;
}

.ligar__ilustracao {
  animation: chegar-cena 0.6s ease-out both;
}

.ligar__titulo {
  margin: 0 20px 6px;
  font-family: var(--chasque-fonte-titulo);
  font-size: 1.4rem;
  font-weight: 650;
  line-height: 1.2;
  color: var(--chasque-tinta);
}

.ligar__texto {
  margin: 0 20px 18px;
  line-height: 1.5;
  color: var(--chasque-tinta-suave);
}

.ligar__form {
  margin: 0 16px;
}

.ligar__rotulo {
  display: block;
  margin: 0 4px 6px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--chasque-tinta);
}

.ligar__campo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 52px;
  padding: 0 16px;
  border-radius: 16px;
  background: var(--chasque-papel);
  border: 1.5px solid var(--chasque-neblina);
  color: var(--chasque-tinta-suave);
  transition: border-color 0.2s ease;
}

.ligar__campo:focus-within {
  border-color: var(--chasque-faixa);
}

.ligar__campo--erro {
  border-color: var(--ion-color-danger);
}

.ligar__campo input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  font: inherit;
  color: var(--chasque-tinta);
  outline: none;
}

.ligar__erro {
  min-height: 1.2em;
  margin: 6px 4px 10px;
  font-size: 0.85rem;
  color: var(--ion-color-danger);
}

.ligar__form .botao ion-spinner {
  width: 18px;
  height: 18px;
  color: inherit;
}

.ligar__form .botao--texto {
  margin-top: 6px;
}

.ligar .secao-titulo {
  margin-top: 28px;
}

.guias {
  margin: 0 16px;
  border-radius: 18px;
  border: 1px solid var(--chasque-neblina);
  background: var(--chasque-papel);
  overflow: hidden;
}

.guia + .guia {
  border-top: 1px solid var(--chasque-neblina);
}

.guia summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 16px;
  list-style: none;
  cursor: pointer;
  font-weight: 600;
  color: var(--chasque-tinta);
}

.guia summary::-webkit-details-marker {
  display: none;
}

.guia__seta {
  color: var(--chasque-tinta-suave);
  transition: transform 0.25s ease;
}

.guia[open] .guia__seta {
  transform: rotate(180deg);
}

.guia ol {
  margin: 0;
  padding: 0 20px 16px 36px;
  color: var(--chasque-tinta-suave);
  line-height: 1.5;
}

.guia li + li {
  margin-top: 6px;
}

.privacidade {
  display: flex;
  gap: 10px;
  margin: 16px 20px 0;
  font-size: 0.85rem;
  line-height: 1.45;
  color: var(--chasque-tinta-suave);
}

.privacidade ion-icon {
  flex: none;
  margin-top: 2px;
  font-size: 16px;
}

.ligada {
  margin: 8px 16px 0;
  padding: 18px 16px;
  border-radius: 22px;
  background: var(--chasque-papel);
  border: 1px solid var(--chasque-neblina);
}

.ligada__cabeca {
  display: flex;
  align-items: center;
  gap: 14px;
}

.ligada__icone {
  flex: none;
  width: 46px;
  height: 46px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-size: 23px;
  color: var(--chasque-faixa-texto);
  background: var(--chasque-faixa);
}

.ligada__erro {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 0.88rem;
  color: var(--ion-color-danger);
  background: color-mix(in srgb, var(--ion-color-danger) 10%, transparent);
}

.ligada__sub {
  margin: 20px 0 10px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--chasque-tinta-suave);
}

.semanas {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.semana {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 11px 14px;
  border-radius: 14px;
  background: var(--chasque-neblina);
  color: var(--chasque-tinta-suave);
  text-decoration: none;
}

.livre .semana {
  background: color-mix(in srgb, var(--chasque-ocre) 18%, var(--chasque-papel));
  color: var(--chasque-tinta);
}

.semana__datas {
  font-family: var(--chasque-fonte-titulo);
  font-weight: 650;
}

.semana__estado {
  font-size: 0.85rem;
}

.ligada__acoes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.ligada__acoes .botao {
  width: auto;
}

.girando {
  animation: girar 0.9s linear infinite;
}

.avisos {
  display: flex;
  gap: 16px;
  align-items: center;
  margin: 0 16px;
  padding: 16px;
  border-radius: 18px;
  background: var(--chasque-papel);
  border: 1px solid var(--chasque-neblina);
}

.avisos span {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.avisos strong {
  color: var(--chasque-tinta);
}

.avisos small {
  font-size: 0.85rem;
  line-height: 1.4;
  color: var(--chasque-tinta-suave);
}

.teste {
  width: auto;
  margin: 10px 20px 0;
  padding: 0;
  color: var(--chasque-tinta-suave);
  text-decoration: underline;
  text-underline-offset: 4px;
}

.desligar {
  margin: 32px auto 24px;
  width: auto;
  padding: 0 18px;
}

@keyframes chegar-cena {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
}

@keyframes girar {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ligar__ilustracao,
  .girando {
    animation: none;
  }
}
</style>
