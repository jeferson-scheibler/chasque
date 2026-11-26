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
- Motivos da comunidade (marcados por pelo menos 3 pessoas em visitas boas) contam como motivos do lugar,
  e valem 25% a mais que os que vêm só do OpenStreetMap: foram confirmados por quem foi.

- Quando a pessoa diz o dia (e, se quiser, a hora), lugares que o horário do OpenStreetMap mostra fechados
  nesse dia saem da lista. Os que não têm horário (a maioria) ficam, com o aviso "sem horário": se alguém
  registrou uma visita ali no mesmo dia da semana, o aviso vira "alguém já foi numa segunda", uma prova de
  que abre (só a contagem de pessoas, nas regras dos motivos da comunidade: a partir de 3 pessoas e só de quem
  ajuda a descrever os lugares). Lugares com horário confirmado valem um pouco mais que os sem.

- Com um tipo escolhido (bar, lanche, restaurante...), entram todos os lugares daquele tipo no raio, tenham
  ou não motivos: o gosto só ordena. Sem isso, um bar sem nenhum motivo no mapa (a maioria) nunca apareceria.
  Nesse modo os já visitados também entram: para marcar um encontro, o bar de sempre serve.

- Na ocasião "evento ou grupo" o que um encontro grande pede soma ao gosto da pessoa: "cabe muita gente"
  (motivo que vem da capacidade no OSM, do tipo de lugar ou de quem já foi) pesa bastante; área aberta, música
  e ambiente animado ajudam; silencioso e aconchegante (que costuma ser pequeno) descontam. Capacidade
  conhecida soma mais quanto maior, e lugar com menos de 20 lugares vale metade. Visitas boas registradas
  como "evento ou grupo" no lugar contam como prova, nas mesmas regras (pessoas diferentes, a partir de 3).
  Todas as provas entram antes do desconto pela distância.

Cada resultado leva os motivos que mais pesaram ("combina com"), para a pessoa entender a sugestão.
"""

import math
from collections import defaultdict

from django.contrib.gis.db.models.functions import Distance
import datetime

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q
from django.contrib.gis.measure import D

from lugares import horarios
from lugares.models import Cidade, Lugar, MotivoComunidade
from salvos.models import Salvo

from .models import PesoGosto, PreferenciaDeclarada, Registro

PESO_PREFERENCIA = 0.75
BONUS_SALVO = 0.5
KM_MEIA_VALIA = 10
RAIO_KM = 30
LIMITE = 20
FATOR_COMUNIDADE = 1.25
FATOR_SEM_HORARIO = 0.85
BASE_DO_TIPO = 0.3  # todo lugar do tipo escolhido começa com isso, para entrar mesmo sem motivo em comum

# tipo -> categorias do OSM (lugares.osm.CATEGORIAS)
TIPOS = {
    "bar": ["amenity=bar", "amenity=pub", "amenity=biergarten", "craft=brewery"],
    "lanche": ["amenity=fast_food", "amenity=food_court"],
    "restaurante": ["amenity=restaurant"],
    "cafe": ["amenity=cafe", "shop=coffee", "shop=bakery", "shop=pastry", "shop=confectionery", "amenity=ice_cream"],
    "noite": ["amenity=nightclub", "amenity=bar", "amenity=pub"],
    "passeio": ["leisure=park", "tourism=viewpoint", "natural=waterfall", "waterway=waterfall", "tourism=attraction",
                "tourism=picnic_site", "leisure=garden", "leisure=nature_reserve"],
}
# o que um evento ou grupo pede, somado ao gosto da pessoa nessa ocasião
GRUPO = "grupo"
PESOS_DE_GRUPO = {"cabe-grupo": 1.5, "ao-ar-livre": 0.4, "musica-ao-vivo": 0.3, "animado": 0.3, "churrasco": 0.2,
                  "silencioso": -0.4, "aconchegante": -0.2}
CAPACIDADE_CHEIA = 150  # a partir daqui o bônus de capacidade não cresce mais
BONUS_CAPACIDADE = 0.6
CAPACIDADE_PEQUENA = 20
BONUS_VISITA_EM_GRUPO = 0.5
MAXIMO_VISITAS_EM_GRUPO = 3
NOTA_BOA = 4
# teto de lugares avaliados por busca (os mais perto): no modo tipo, uma capital tem milhares no raio
MAXIMO_CANDIDATOS = 400
POR_CATEGORIA_NO_TOPO = 2
TOPO = 10


def raridade():
    """{slug: fator} pelo quanto o motivo é raro entre os lugares. Guardado em cache por 1 hora."""
    fatores = cache.get("chasque:raridade-motivos")
    if fatores is None:
        total = Lugar.objects.count() or 1
        # lugares com cada motivo, vindo do OSM ou da comunidade (sem contar o mesmo lugar duas vezes)
        pares = set(Lugar.tags.through.objects.values_list("lugar_id", "tag__slug"))
        pares |= set(MotivoComunidade.objects.values_list("lugar_id", "tag__slug"))
        contagem = defaultdict(int)
        for _, slug in pares:
            contagem[slug] += 1
        fatores = {slug: 1 + math.log10((total + 1) / (n + 1)) / 2 for slug, n in contagem.items()}
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


def semana_django(data):
    """Dia da semana no filtro `visitado_em__week_day` do Django: 1 = domingo ... 7 = sábado."""
    return (data.weekday() + 1) % 7 + 1


def pessoas_que_foram(lugar_ids, **filtro):
    """{lugar_id: pessoas diferentes} com visitas que batem com o filtro, nas mesmas regras dos motivos da
    comunidade: só quem deixou "Ajudar a descrever os lugares" ligado, contas ativas, e só a partir de
    MOTIVOS_MIN_PESSOAS pessoas (abaixo disso daria para saber quem esteve lá). Conta pessoas, não visitas:
    uma conta sozinha não infla um lugar."""
    if not lugar_ids:
        return {}
    contagem = (
        Registro.objects.filter(lugar_id__in=lugar_ids, usuario__contribuir_motivos=True, usuario__is_active=True,
                                **filtro)
        .values("lugar_id")
        .annotate(pessoas=Count("usuario", distinct=True))
    )
    return {c["lugar_id"]: c["pessoas"] for c in contagem if c["pessoas"] >= settings.MOTIVOS_MIN_PESSOAS}


def horario_do_lugar(lugar, quando, hora):
    """('aberto' | 'fechado' | None, texto do dia) pelo horário do OpenStreetMap."""
    situacao = horarios.estado(lugar.horario, quando, hora)
    return situacao, (horarios.texto_do_dia(lugar.horario, quando) if situacao == "aberto" else "")


def sugerir(usuario, origem, ocasiao="", raio_km=RAIO_KM, limite=LIMITE, quando=None, hora=None, tipo=""):
    """`quando` é um date (ou None), `hora` os minutos desde 00:00 (ou None = qualquer hora) e `tipo` uma
    chave de TIPOS (ou "" = pelo gosto)."""
    pesos = pesos_da_pessoa(usuario, ocasiao)
    if ocasiao == GRUPO:
        for slug, peso in PESOS_DE_GRUPO.items():
            pesos[slug] = pesos.get(slug, 0) + peso
    positivos = [slug for slug, peso in pesos.items() if peso > 0]
    if origem is None or (not positivos and not tipo):
        return []

    salvos = set(Salvo.objects.filter(usuario=usuario, lugar__isnull=False).values_list("lugar_id", flat=True))
    candidatos = Lugar.objects.filter(ponto__dwithin=(origem["ponto"], D(km=raio_km)))
    if tipo:
        candidatos = candidatos.filter(categoria__in=TIPOS[tipo])
    else:
        candidatos = (candidatos.filter(Q(tags__slug__in=positivos) | Q(motivos_comunidade__tag__slug__in=positivos))
                      .exclude(id__in=Registro.objects.filter(usuario=usuario).values("lugar_id")))
    candidatos = (
        candidatos
        .distinct()
        .annotate(distancia=Distance("ponto", origem["ponto"]))
        .order_by("distancia")
        .prefetch_related("tags", "motivos_comunidade__tag")
    )[:MAXIMO_CANDIDATOS]

    fator = raridade()
    resultados = []
    for lugar in candidatos:
        comunidade = {m.tag.slug: m.pessoas for m in lugar.motivos_comunidade.all()}
        slugs = sorted({t.slug for t in lugar.tags.all()} | set(comunidade))

        def valor(s):
            return pesos.get(s, 0) * fator.get(s, 1) * (FATOR_COMUNIDADE if s in comunidade else 1)

        pontos = sum(valor(s) for s in slugs) + (BASE_DO_TIPO if tipo else 0)
        if lugar.id in salvos:
            pontos += BONUS_SALVO
        if ocasiao == GRUPO and lugar.capacidade:
            if lugar.capacidade < CAPACIDADE_PEQUENA:
                pontos *= 0.5
            else:
                pontos += BONUS_CAPACIDADE * min(lugar.capacidade, CAPACIDADE_CHEIA) / CAPACIDADE_CHEIA
        if pontos <= 0:
            continue
        horario = None
        if quando:
            situacao, texto = horario_do_lugar(lugar, quando, hora)
            if situacao == "fechado":
                continue
            horario = {"estado": "aberto", "texto": texto} if situacao == "aberto" else {"estado": "sem_info", "texto": ""}
        combina = sorted((s for s in slugs if pesos.get(s, 0) > 0), key=lambda s: (-valor(s), s))[:3]
        resultados.append({
            "lugar": lugar,
            "bruto": pontos,  # antes da distância; vira "pontos" no fim, depois das provas
            "combina": combina,
            "comunidade": {s: comunidade[s] for s in combina if s in comunidade},
            "salvo": lugar.id in salvos,
            "horario": horario,
            "grupo": {"capacidade": lugar.capacidade, "visitas": 0} if ocasiao == GRUPO else None,
        })

    if ocasiao == GRUPO:
        em_grupo = pessoas_que_foram([r["lugar"].id for r in resultados], ocasiao=GRUPO, nota__gte=NOTA_BOA)
        for r in resultados:
            n = em_grupo.get(r["lugar"].id, 0)
            if n:
                r["grupo"]["visitas"] = n
                r["bruto"] += BONUS_VISITA_EM_GRUPO * min(n, MAXIMO_VISITAS_EM_GRUPO)

    if quando:
        sem_info = [r for r in resultados if r["horario"]["estado"] == "sem_info"]
        vistos = pessoas_que_foram([r["lugar"].id for r in sem_info], visitado_em__week_day=semana_django(quando))
        for r in sem_info:
            n = vistos.get(r["lugar"].id, 0)
            if n:
                r["horario"] = {"estado": "visto", "texto": "", "visitas": n}  # prova de que abre: sem o desconto
            else:
                r["bruto"] *= FATOR_SEM_HORARIO

    for r in resultados:
        r["pontos"] = round(r.pop("bruto") / (1 + r["lugar"].distancia.km / KM_MEIA_VALIA), 4)

    resultados.sort(key=lambda r: (-r["pontos"], r["lugar"].distancia.m, r["lugar"].nome))
    return variar(resultados, limite)
