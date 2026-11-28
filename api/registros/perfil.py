"""Perfil de gosto: quanto cada motivo (tag) pesa para a pessoa, no geral e por ocasião.

Regra do MVP, simples e explicável: cada visita soma (nota - 3) / 2 a cada motivo marcado.
Nota 5 soma +1, nota 3 não muda nada, nota 1 soma -1. O mesmo valor vale para o perfil geral
(ocasião vazia) e para a ocasião da visita. As sugestões leem esses pesos.

Quando a visita veio de um link salvo com motivo (salvos.Intencao), a pessoa diz se ele valeu.
Os motivos da intenção somam +0,5 (valeu), 0 (mais ou menos) ou -0,5 (não), além do que a nota já
soma. É o que separa "o lugar é bom" de "o lugar é bom para o que eu procuro".
"""

from collections import defaultdict

from django.db import transaction

from .models import Expectativa, PesoGosto, Registro


def contribuicao(nota):
    return (nota - 3) / 2


PESO_DA_EXPECTATIVA = {Expectativa.SIM: 0.5, Expectativa.MEIO: 0.0, Expectativa.NAO: -0.5}


@transaction.atomic
def recalcular_perfil(usuario):
    pesos = defaultdict(float)
    for registro in Registro.objects.filter(usuario=usuario).select_related("intencao").prefetch_related(
        "tags", "intencao__tags"
    ):
        valor = contribuicao(registro.nota)
        for tag in registro.tags.all():
            pesos[(tag.id, "")] += valor
            pesos[(tag.id, registro.ocasiao)] += valor
        extra = PESO_DA_EXPECTATIVA.get(registro.expectativa, 0.0) if registro.intencao else 0.0
        if extra:
            for tag in registro.intencao.tags.all():
                pesos[(tag.id, "")] += extra
                pesos[(tag.id, registro.ocasiao)] += extra

    PesoGosto.objects.filter(usuario=usuario).delete()
    PesoGosto.objects.bulk_create(
        PesoGosto(usuario=usuario, tag_id=tag_id, ocasiao=ocasiao, peso=round(peso, 4))
        for (tag_id, ocasiao), peso in pesos.items()
        if peso != 0
    )
