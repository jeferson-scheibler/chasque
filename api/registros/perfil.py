"""Perfil de gosto: quanto cada motivo (tag) pesa para a pessoa, no geral e por ocasião.

Regra do MVP, simples e explicável: cada visita soma (nota - 3) / 2 a cada motivo marcado.
Nota 5 soma +1, nota 3 não muda nada, nota 1 soma -1. O mesmo valor vale para o perfil geral
(ocasião vazia) e para a ocasião da visita. As sugestões leem esses pesos.
"""

from collections import defaultdict

from django.db import transaction

from .models import PesoGosto, Registro


def contribuicao(nota):
    return (nota - 3) / 2


@transaction.atomic
def recalcular_perfil(usuario):
    pesos = defaultdict(float)
    for registro in Registro.objects.filter(usuario=usuario).prefetch_related("tags"):
        valor = contribuicao(registro.nota)
        for tag in registro.tags.all():
            pesos[(tag.id, "")] += valor
            pesos[(tag.id, registro.ocasiao)] += valor

    PesoGosto.objects.filter(usuario=usuario).delete()
    PesoGosto.objects.bulk_create(
        PesoGosto(usuario=usuario, tag_id=tag_id, ocasiao=ocasiao, peso=round(peso, 4))
        for (tag_id, ocasiao), peso in pesos.items()
        if peso != 0
    )
