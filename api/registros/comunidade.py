"""Motivos da comunidade: o que as visitas bem avaliadas dizem de cada lugar, somado e anônimo.

- Contam só visitas de 4 ou 5 sóis: numa visita ruim os motivos respondem "o que não funcionou?".
- Um motivo só descreve o lugar quando pelo menos MOTIVOS_MIN_PESSOAS pessoas diferentes o marcaram.
- Fica de fora quem desligou "Ajudar a descrever os lugares" e contas desativadas.
- Guarda só a contagem de pessoas, nunca quem foram.
"""

from django.conf import settings
from django.db import transaction
from django.db.models import Count

from lugares.models import MotivoComunidade

from .models import Registro

NOTA_MINIMA = 4


@transaction.atomic
def recalcular_motivos_do_lugar(lugar_id):
    contagem = (
        Registro.objects.filter(
            lugar_id=lugar_id,
            nota__gte=NOTA_MINIMA,
            usuario__contribuir_motivos=True,
            usuario__is_active=True,
            tags__isnull=False,
        )
        .values("tags")
        .annotate(pessoas=Count("usuario", distinct=True))
    )
    validos = {c["tags"]: c["pessoas"] for c in contagem if c["pessoas"] >= settings.MOTIVOS_MIN_PESSOAS}

    MotivoComunidade.objects.filter(lugar_id=lugar_id).exclude(tag_id__in=validos).delete()
    for tag_id, pessoas in validos.items():
        MotivoComunidade.objects.update_or_create(lugar_id=lugar_id, tag_id=tag_id, defaults={"pessoas": pessoas})


def recalcular_motivos(lugar_ids):
    for lugar_id in set(lugar_ids):
        recalcular_motivos_do_lugar(lugar_id)


def lugares_de(usuario):
    return list(Registro.objects.filter(usuario=usuario).values_list("lugar_id", flat=True).distinct())
