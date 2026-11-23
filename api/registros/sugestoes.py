"""Sugestões de lugares pelo gosto da pessoa.

Regra do MVP, explicável em uma frase: cada lugar soma o peso que a pessoa dá aos motivos que ele tem.

- Peso de um motivo = perfil de gosto (das visitas) + 0,75 se a pessoa marcou o motivo como preferência.
  Com uma ocasião escolhida, vale o peso daquela ocasião mais metade do peso geral.
- O lugar precisa somar mais que zero. Salvos em "Quero conhecer" ganham +0,5.
- A distância desconta: pontos / (1 + km / 10). A 10 km, o lugar vale metade.
- Lugares que a pessoa já visitou ficam de fora: a ideia é achar o próximo.
- Motivo raro na base vale mais que motivo comum: "natureza" está em centenas de praças, "cerveja
  artesanal" em poucos lugares. Fator = 1 + log10(total / lugares com o motivo) / 2.
- Variedade: no topo, no máximo 2 lugares da mesma categoria; os demais vêm depois.

Cada resultado leva os motivos que mais pesaram ("combina com"), para a pessoa entender a sugestão.
"""

import math
from collections import defaultdict

from django.contrib.gis.db.models.functions import Distance
from django.core.cache import cache
from django.db.models import Count
from django.contrib.gis.measure import D

from lugares.models import Cidade, Lugar
from salvos.models import Salvo

from .models import PesoGosto, PreferenciaDeclarada, Registro

PESO_PREFERENCIA = 0.75
BONUS_SALVO = 0.5
KM_MEIA_VALIA = 10
RAIO_KM = 30
LIMITE = 20
POR_CATEGORIA_NO_TOPO = 2
TOPO = 10


def raridade():
    """{slug: fator} pelo quanto o motivo é raro entre os lugares. Guardado em cache por 1 hora."""
    fatores = cache.get("chasque:raridade-motivos")
    if fatores is None:
        total = Lugar.objects.count() or 1
        contagem = Lugar.tags.through.objects.values("tag__slug").annotate(n=Count("id"))
        fatores = {c["tag__slug"]: 1 + math.log10((total + 1) / (c["n"] + 1)) / 2 for c in contagem}
        cache.set("chasque:raridade-motivos", fatores, 3600)
    return fatores


def variar(resultados, limite):
    """Mantém a ordem, mas no topo não deixa uma categoria ocupar mais que POR_CATEGORIA_NO_TOPO vagas."""
    topo, resto, por_categoria = [], [], defaultdict(int)
    for r in resultados:
        categoria = r["lugar"].categoria
        if len(topo) < TOPO and por_categoria[categoria] < POR_CATEGORIA_NO_TOPO:
            topo.append(r)
            por_categoria[categoria] += 1
        else:
            resto.append(r)
    return (topo + resto)[:limite]


def pesos_da_pessoa(usuario, ocasiao=""):
    gerais, da_ocasiao = defaultdict(float), defaultdict(float)
    for p in PesoGosto.objects.filter(usuario=usuario).select_related("tag"):
        if p.ocasiao == "":
            gerais[p.tag.slug] = p.peso
        elif p.ocasiao == ocasiao:
            da_ocasiao[p.tag.slug] = p.peso

    pesos = defaultdict(float)
    for slug, peso in gerais.items():
        pesos[slug] += peso * (0.5 if ocasiao else 1)
    for slug, peso in da_ocasiao.items():
        pesos[slug] += peso
    for slug in PreferenciaDeclarada.objects.filter(usuario=usuario).values_list("tag__slug", flat=True):
        pesos[slug] += PESO_PREFERENCIA
    return dict(pesos)


def origem_da_busca(usuario, ponto=None, cidade=None):
    """De onde procurar: posição informada, cidade escolhida, cidade da pessoa ou a última visita."""
    if ponto is not None:
        return {"tipo": "localizacao", "nome": "Perto de você", "ponto": ponto}
    if cidade is not None:
        return {"tipo": "cidade", "nome": cidade.nome, "ponto": cidade.ponto, "cidade_id": cidade.id}
    if usuario.cidade_base:
        cidade = Cidade.objects.filter(nome__iexact=usuario.cidade_base.strip()).first()
        if cidade:
            return {"tipo": "cidade", "nome": cidade.nome, "ponto": cidade.ponto, "cidade_id": cidade.id}
    ultima = Registro.objects.filter(usuario=usuario).select_related("lugar").order_by("-visitado_em", "-id").first()
    if ultima:
        return {"tipo": "ultima_visita", "nome": ultima.lugar.cidade or ultima.lugar.nome, "ponto": ultima.lugar.ponto}
    return None


def sugerir(usuario, origem, ocasiao="", raio_km=RAIO_KM, limite=LIMITE):
    pesos = pesos_da_pessoa(usuario, ocasiao)
    positivos = [slug for slug, peso in pesos.items() if peso > 0]
    if origem is None or not positivos:
        return []

    visitados = Registro.objects.filter(usuario=usuario).values("lugar_id")
    salvos = set(Salvo.objects.filter(usuario=usuario, lugar__isnull=False).values_list("lugar_id", flat=True))
    candidatos = (
        Lugar.objects.filter(ponto__dwithin=(origem["ponto"], D(km=raio_km)), tags__slug__in=positivos)
        .exclude(id__in=visitados)
        .distinct()
        .annotate(distancia=Distance("ponto", origem["ponto"]))
        .prefetch_related("tags")
    )

    fator = raridade()
    resultados = []
    for lugar in candidatos:
        slugs = [t.slug for t in lugar.tags.all()]
        pontos = sum(pesos.get(s, 0) * fator.get(s, 1) for s in slugs)
        if lugar.id in salvos:
            pontos += BONUS_SALVO
        if pontos <= 0:
            continue
        km = lugar.distancia.km
        combina = sorted(
            (s for s in slugs if pesos.get(s, 0) > 0), key=lambda s: (-pesos[s] * fator.get(s, 1), s)
        )[:3]
        resultados.append({
            "lugar": lugar,
            "pontos": round(pontos / (1 + km / KM_MEIA_VALIA), 4),
            "combina": combina,
            "salvo": lugar.id in salvos,
        })

    resultados.sort(key=lambda r: (-r["pontos"], r["lugar"].distancia.m, r["lugar"].nome))
    return variar(resultados, limite)
