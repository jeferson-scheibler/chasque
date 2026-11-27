"""Busca de lugares por nome: sem acento e tolerante a erro de digitação (unaccent + pg_trgm)."""

import unicodedata

from django.contrib.postgres.search import TrigramWordSimilarity
from django.db.models import Func, Q, Value

SEMELHANCA_MINIMA = 0.4


class Unaccent(Func):
    function = "unaccent"


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def por_nome(lugares, q):
    """Filtra pelo nome e anota `semelhanca` (0 a 1). `q` já deve vir sem acento."""
    return lugares.annotate(semelhanca=TrigramWordSimilarity(Value(q), Unaccent("nome"))).filter(
        Q(nome__unaccent__icontains=q) | Q(semelhanca__gte=SEMELHANCA_MINIMA)
    )
