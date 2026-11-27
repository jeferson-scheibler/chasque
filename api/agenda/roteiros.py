"""Monta o roteiro de um dia livre com os lugares que a pessoa salvou e ainda não visitou.

1. Candidatos: lugares salvos, ainda sem visita, que não fecham nesse dia (pelo horário do OpenStreetMap).
2. Escolhe o lugar com mais salvos por perto (RAIO_KM) como centro do dia; lugares que já estiveram em
   outro roteiro recente valem menos, para o próximo fim de semana não repetir o anterior.
3. Se faltar parada, completa com sugestões do Chasque perto do centro, para o mesmo dia.
4. Põe na ordem de um dia: café de manhã, restaurante no almoço, passeio à tarde, bar à noite. Se o lugar
   está fechado no horário do seu momento, ele vai para outro momento em que está aberto.
"""

import math
from datetime import timedelta

from django.db.models import Q

from lugares import horarios
from lugares.models import Cidade, Lugar
from registros.models import Registro
from registros.sugestoes import sugerir

from .models import Parada, Roteiro

RAIO_KM = 20
MAXIMO_PARADAS = 4
MINIMO_PARADAS = 2
QUER_PARADAS = 3  # completa com sugestões até aqui
PESO_REPETIDO = 0.4
DIAS_DE_MEMORIA = 28

HOSPEDAGEM = {"tourism=hotel", "tourism=guest_house", "tourism=hostel", "tourism=motel", "tourism=chalet",
              "tourism=camp_site"}
MOMENTOS = ["manha", "almoco", "tarde", "noite"]
HORA_DO_MOMENTO = {"manha": 10 * 60, "almoco": 12 * 60 + 30, "tarde": 15 * 60 + 30, "noite": 20 * 60}
MOMENTO_DA_CATEGORIA = {
    "amenity=cafe": "manha", "shop=coffee": "manha", "shop=bakery": "manha", "shop=pastry": "manha",
    "amenity=marketplace": "manha", "shop=farm": "manha", "shop=cheese": "manha",
    "amenity=restaurant": "almoco", "amenity=food_court": "almoco",
    "amenity=bar": "noite", "amenity=pub": "noite", "amenity=nightclub": "noite", "amenity=biergarten": "noite",
    "craft=brewery": "noite", "amenity=theatre": "noite", "amenity=cinema": "noite",
}


def km(a, b):
    """Distância em linha reta entre dois lugares (haversine)."""
    lng1, lat1, lng2, lat2 = map(math.radians, (a.ponto.x, a.ponto.y, b.ponto.x, b.ponto.y))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def momento(lugar, dia):
    """Momento do dia em que a parada cabe, ou None se o lugar está fechado em todos."""
    preferido = MOMENTO_DA_CATEGORIA.get(lugar.categoria, "tarde")
    ordem = [preferido] + [m for m in MOMENTOS if m != preferido]
    for m in ordem:
        if horarios.estado(lugar.horario, dia, HORA_DO_MOMENTO[m]) != "fechado":
            return m
    return None


def candidatos_salvos(usuario, dia):
    lugares = (
        Lugar.objects.filter(salvos__usuario=usuario)
        .exclude(id__in=Registro.objects.filter(usuario=usuario).values("lugar_id"))
        .exclude(categoria__in=HOSPEDAGEM)
        .distinct()
    )
    return [l for l in lugares.order_by("id") if horarios.estado(l.horario, dia) != "fechado"]


def recentes(usuario, dia):
    """Lugares que já apareceram em roteiros perto desse dia (antes ou depois)."""
    perto = Q(roteiro__dia__gte=dia - timedelta(days=DIAS_DE_MEMORIA), roteiro__dia__lte=dia + timedelta(days=DIAS_DE_MEMORIA))
    return set(
        Parada.objects.filter(perto, roteiro__usuario=usuario).exclude(roteiro__dia=dia).values_list("lugar_id", flat=True)
    )


def escolher_centro(candidatos, ja_usados):
    """O lugar com mais salvos em volta; no empate, o que deixa as paradas mais juntas."""
    def nota(centro):
        vizinhos = [o for o in candidatos if km(centro, o) <= RAIO_KM]
        total = sum(1 if o.id not in ja_usados else PESO_REPETIDO for o in vizinhos)
        return total, -sum(km(centro, o) for o in vizinhos)

    return max(candidatos, key=nota)


def ordenar(paradas):
    """Momentos na ordem do dia e, dentro de cada um, o mais perto da parada anterior primeiro."""
    saida = []
    for m in MOMENTOS:
        restantes = [p for p in paradas if p["momento"] == m]
        while restantes:
            if saida:
                proxima = min(restantes, key=lambda p: km(saida[-1]["lugar"], p["lugar"]))
            else:
                proxima = restantes[0]
            restantes.remove(proxima)
            saida.append(proxima)
    return saida


def montar(usuario, dia):
    """Lista de paradas [{lugar, momento, salvo}] na ordem, ou [] se não dá para montar um roteiro."""
    candidatos = candidatos_salvos(usuario, dia)
    if not candidatos:
        return []
    centro = escolher_centro(candidatos, recentes(usuario, dia))
    perto = sorted((c for c in candidatos if km(centro, c) <= RAIO_KM), key=lambda c: km(centro, c))

    paradas = []
    usados = set()
    for lugar in perto:
        m = momento(lugar, dia)
        if m is None or sum(p["momento"] == m for p in paradas) >= 2:
            continue
        paradas.append({"lugar": lugar, "momento": m, "salvo": True})
        usados.add(lugar.id)
        if len(paradas) == MAXIMO_PARADAS:
            break

    if len(paradas) < QUER_PARADAS:
        origem = {"tipo": "roteiro", "nome": centro.cidade or centro.nome, "ponto": centro.ponto}
        sugestoes = sugerir(usuario, origem, raio_km=RAIO_KM, limite=12, quando=dia)
        # primeiro o que preenche um momento vazio, depois o resto pela ordem da sugestão
        cobertos = {p["momento"] for p in paradas}
        extras = []
        for s in sugestoes:
            lugar = s["lugar"]
            if lugar.id in usados or lugar.categoria in HOSPEDAGEM:
                continue
            m = momento(lugar, dia)
            if m:
                extras.append((m in cobertos, {"lugar": lugar, "momento": m, "salvo": False}))
        for _, parada in sorted(extras, key=lambda e: e[0]):
            if len(paradas) >= QUER_PARADAS:
                break
            if sum(p["momento"] == parada["momento"] for p in paradas) >= 2:
                continue
            paradas.append(parada)
            usados.add(parada["lugar"].id)

    if len(paradas) < MINIMO_PARADAS:
        return []
    return ordenar(paradas)


def cidade_do_roteiro(paradas, base=""):
    """(cidade, viagem). Se alguma parada fica na cidade da pessoa, o roteiro é de lá e não é viagem; senão é a
    cidade com mais paradas (no empate, a da primeira)."""
    cidades = [p["lugar"].cidade for p in paradas if p["lugar"].cidade]
    if not cidades:
        return "", False
    base = (base or "").strip().lower()
    if base and any(c.lower() == base for c in cidades):
        return next(c for c in cidades if c.lower() == base), False
    cidade = max(dict.fromkeys(cidades), key=cidades.count)
    # sem cidade base conhecida não dá para dizer que é viagem
    viagem = bool(base) and Cidade.objects.filter(nome__iexact=base).exists()
    return cidade, viagem


def criar(usuario, dia):
    """Cria (ou devolve) o roteiro do dia. None se não há lugares para isso."""
    existente = Roteiro.objects.filter(usuario=usuario, dia=dia).first()
    if existente:
        return existente
    paradas = montar(usuario, dia)
    if not paradas:
        return None
    cidade, viagem = cidade_do_roteiro(paradas, usuario.cidade_base)
    roteiro = Roteiro.objects.create(usuario=usuario, dia=dia, cidade=cidade, viagem=viagem)
    Parada.objects.bulk_create([
        Parada(roteiro=roteiro, lugar=p["lugar"], ordem=i, momento=p["momento"], salvo=p["salvo"])
        for i, p in enumerate(paradas)
    ])
    return roteiro
