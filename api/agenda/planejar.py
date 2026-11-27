"""Lê as agendas, acha os fins de semana livres, monta os roteiros e avisa a pessoa."""

from datetime import date, timedelta

from django.utils import timezone

from . import ical, push
from .livres import SEMANAS, dias_livres
from .models import Agenda, Roteiro
from .roteiros import criar

LER_A_CADA = timedelta(hours=6)
AVISAR_ANTES_DIAS = 3  # o aviso sai de quarta em diante para o sábado
HORAS_DE_AVISO = range(9, 21)  # ninguém recebe aviso de madrugada
DIAS_DA_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def ler(agenda, hoje=None):
    """Baixa a agenda e atualiza os roteiros. Levanta ical.AgendaInvalida se não deu para ler."""
    hoje = hoje or timezone.localdate()
    try:
        dados = ical.baixar(agenda.url)
        ocupados = ical.ocupados(dados, hoje, hoje + timedelta(days=7 * SEMANAS + 2))
    except ical.AgendaInvalida as erro:
        agenda.erro = str(erro)[:200]
        agenda.lida_em = timezone.now()
        if agenda.pk:
            agenda.save(update_fields=["erro", "lida_em"])
        raise
    agenda.dias_livres = [d.isoformat() for d in dias_livres(hoje, ocupados)]
    agenda.erro = ""
    agenda.lida_em = timezone.now()
    agenda.save()
    atualizar_roteiros(agenda.usuario, agenda.dias_livres, hoje)
    return agenda


def atualizar_roteiros(usuario, livres, hoje):
    """Tira os roteiros de dias que deixaram de ser livres e cria os que faltam."""
    livres = {date.fromisoformat(d) for d in livres}
    Roteiro.objects.filter(usuario=usuario, dia__gt=hoje).exclude(dia__in=livres).delete()
    for dia in sorted(livres):
        if dia > hoje:
            criar(usuario, dia)


def nomes(lista):
    return lista[0] if len(lista) == 1 else ", ".join(lista[:-1]) + " e " + lista[-1]


def mensagem(roteiro):
    """(título, corpo) do aviso."""
    dia = DIAS_DA_SEMANA[roteiro.dia.weekday()]
    paradas = [p.lugar.nome for p in roteiro.paradas.select_related("lugar")]
    lista = nomes(paradas[:3]) + (f" e mais {len(paradas) - 3}" if len(paradas) > 3 else "")
    if roteiro.viagem and roteiro.cidade:
        return (f"Bate e volta para {roteiro.cidade}?",
                f"{dia} livre na agenda. Preparamos um roteiro especial com {lista}.")
    return ("Aproveite o fim de semana",
            f"{dia} livre na agenda. Curta esse roteiro especial: {lista}.")


def avisar_pendentes(agora=None):
    agora = timezone.localtime(agora)
    if agora.hour not in HORAS_DE_AVISO:
        return 0
    hoje = agora.date()
    avisados = 0
    pendentes = Roteiro.objects.filter(
        notificado_em__isnull=True, dispensado_em__isnull=True, visto_em__isnull=True,
        dia__gt=hoje, dia__lte=hoje + timedelta(days=AVISAR_ANTES_DIAS), usuario__is_active=True,
    ).select_related("usuario")
    for roteiro in pendentes:
        titulo, corpo = mensagem(roteiro)
        if push.enviar(roteiro.usuario, titulo, corpo, f"/abas/sugestoes/roteiro/{roteiro.id}", f"roteiro-{roteiro.id}"):
            roteiro.notificado_em = timezone.now()
            roteiro.save(update_fields=["notificado_em"])
            avisados += 1
    return avisados


def planejar(agora=None, forcar=False):
    """Uma rodada: o agendador chama de hora em hora."""
    agora = agora or timezone.now()
    lidas = 0
    for agenda in Agenda.objects.select_related("usuario").filter(usuario__is_active=True):
        if forcar or agenda.lida_em is None or agora - agenda.lida_em >= LER_A_CADA:
            try:
                ler(agenda, timezone.localtime(agora).date())
                lidas += 1
            except ical.AgendaInvalida:
                pass  # o erro fica na agenda e aparece no app
    return lidas, avisar_pendentes(agora)
