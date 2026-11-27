"""Quais sábados e domingos estão livres na agenda."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings

# Um dia de fim de semana é livre se nada ocupa a janela em que um passeio acontece.
JANELA = (time(10, 0), time(20, 0))
SEMANAS = 3


def fins_de_semana(hoje, semanas=SEMANAS):
    """[(sábado, domingo)] dos próximos fins de semana, a partir de amanhã."""
    saida = []
    sabado = hoje + timedelta(days=(5 - hoje.weekday()) % 7)
    if sabado <= hoje:  # hoje é sábado: o de hoje já começou
        sabado += timedelta(days=7)
    if hoje.weekday() == 5:  # sábado: ainda dá o domingo de amanhã
        saida.append((None, hoje + timedelta(days=1)))
    while len(saida) < semanas:
        saida.append((sabado, sabado + timedelta(days=1)))
        sabado += timedelta(days=7)
    return saida


def dia_livre(dia, ocupados):
    fuso = ZoneInfo(settings.TIME_ZONE)
    inicio = datetime.combine(dia, JANELA[0], tzinfo=fuso)
    fim = datetime.combine(dia, JANELA[1], tzinfo=fuso)
    return not any(a < fim and b > inicio for a, b in ocupados)


def dias_livres(hoje, ocupados, semanas=SEMANAS):
    """Um dia por fim de semana: o sábado se estiver livre, senão o domingo; fins de semana cheios ficam de fora."""
    escolhidos = []
    for sabado, domingo in fins_de_semana(hoje, semanas):
        for dia in (sabado, domingo):
            if dia and dia_livre(dia, ocupados):
                escolhidos.append(dia)
                break
    return escolhidos
