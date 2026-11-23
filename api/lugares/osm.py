"""Importação de lugares do OpenStreetMap.

Fluxo: arquivo .osm.pbf (Geofabrik) -> osmium recorta a região e filtra as categorias
-> osmium exporta GeoJSON -> este módulo classifica e grava Lugar e Cidade.

Licença: dados do OSM são ODbL. A atribuição "© colaboradores do OpenStreetMap"
precisa aparecer onde os lugares são mostrados.
"""

import json
import math
import subprocess
import tempfile
from pathlib import Path

from django.contrib.gis.geos import GEOSGeometry, Point
from django.db import transaction

from .models import Cidade, Lugar, Tag

# oeste, sul, leste, norte. Vale do Taquari e arredores.
BBOX_VALE = (-52.40, -29.85, -51.65, -28.80)

# chave=valor do OSM -> nome mostrado no app.
CATEGORIAS = {
    "amenity=restaurant": "Restaurante",
    "amenity=cafe": "Café",
    "amenity=bar": "Bar",
    "amenity=pub": "Bar",
    "amenity=fast_food": "Lanchonete",
    "amenity=ice_cream": "Sorveteria",
    "amenity=biergarten": "Cervejaria ao ar livre",
    "amenity=food_court": "Praça de alimentação",
    "amenity=theatre": "Teatro",
    "amenity=arts_centre": "Centro cultural",
    "amenity=cinema": "Cinema",
    "amenity=nightclub": "Casa noturna",
    "amenity=marketplace": "Feira",
    "tourism=attraction": "Atração",
    "tourism=museum": "Museu",
    "tourism=viewpoint": "Mirante",
    "tourism=gallery": "Galeria",
    "tourism=hotel": "Hotel",
    "tourism=guest_house": "Pousada",
    "tourism=hostel": "Hostel",
    "tourism=motel": "Motel",
    "tourism=chalet": "Chalé",
    "tourism=camp_site": "Camping",
    "tourism=picnic_site": "Área de piquenique",
    "tourism=theme_park": "Parque temático",
    "tourism=zoo": "Zoológico",
    "shop=bakery": "Padaria",
    "shop=pastry": "Confeitaria",
    "shop=confectionery": "Doceria",
    "shop=chocolate": "Chocolateria",
    "shop=coffee": "Café",
    "shop=wine": "Loja de vinhos",
    "shop=cheese": "Queijaria",
    "shop=farm": "Produtor rural",
    "shop=deli": "Empório",
    "shop=craft": "Artesanato",
    "shop=art": "Arte",
    "shop=gift": "Presentes",
    "shop=books": "Livraria",
    "craft=winery": "Vinícola",
    "craft=brewery": "Cervejaria",
    "craft=distillery": "Destilaria",
    "leisure=park": "Parque",
    "leisure=nature_reserve": "Reserva natural",
    "leisure=garden": "Jardim",
    "leisure=water_park": "Parque aquático",
    "natural=waterfall": "Cachoeira",
    "waterway=waterfall": "Cachoeira",
    "historic=monument": "Monumento",
    "historic=memorial": "Memorial",
    "historic=ruins": "Ruínas",
    "historic=castle": "Castelo",
    "historic=archaeological_site": "Sítio arqueológico",
    "historic=building": "Prédio histórico",
    "historic=manor": "Casarão histórico",
    "historic=mill": "Moinho histórico",
}

def nome_da_categoria(categoria):
    return CATEGORIAS.get(categoria, "")


def classificar(tags):
    """Primeira categoria conhecida do objeto, ou None se não interessa ao Chasque."""
    if tags.get("access") in ("private", "no"):  # jardim de casa, área particular
        return None
    for chave in ("amenity", "tourism", "craft", "shop", "leisure", "natural", "waterway", "historic"):
        valor = tags.get(chave)
        if valor and f"{chave}={valor}" in CATEGORIAS:
            return f"{chave}={valor}"
    return None


def _sim(tags, chave):
    return tags.get(chave, "").lower() in ("yes", "only", "designated")


def tags_iniciais(tags, categoria):
    """Motivos que dá para deduzir dos dados do OSM. Conservador de propósito."""
    chave, valor = categoria.split("=", 1)
    slugs = set()

    if categoria == "tourism=viewpoint":
        slugs.add("vista-bonita")
    if categoria in ("leisure=park", "leisure=nature_reserve", "leisure=garden", "natural=waterfall",
                     "waterway=waterfall", "tourism=picnic_site", "tourism=camp_site"):
        slugs |= {"natureza", "ao-ar-livre"}
    if chave == "historic" or categoria == "tourism=museum":
        slugs |= {"historico", "cultura-local"}
    if categoria in ("tourism=gallery", "amenity=arts_centre", "amenity=theatre", "shop=art"):
        slugs |= {"arte", "cultura-local"}
    if categoria == "craft=brewery" or _sim(tags, "microbrewery"):
        slugs.add("cerveja-artesanal")
    if categoria in ("craft=winery", "shop=wine"):
        slugs.add("vinho")
    if categoria in ("shop=bakery", "shop=pastry", "shop=confectionery", "shop=chocolate", "amenity=ice_cream"):
        slugs.add("doces")
    if categoria in ("shop=farm", "shop=cheese", "craft=winery", "craft=distillery", "amenity=marketplace"):
        slugs.add("produtor-local")
    if categoria == "shop=coffee":
        slugs.add("cafe-especial")
    if categoria == "amenity=biergarten":
        slugs.add("ao-ar-livre")
    if categoria == "amenity=nightclub":
        slugs.add("animado")

    cozinha = {c.strip().lower() for c in tags.get("cuisine", "").split(";")}
    if cozinha & {"barbecue", "steak_house", "churrasco", "churrascaria"}:
        slugs.add("churrasco")
    if cozinha & {"regional", "brazilian", "homestyle"}:
        slugs.add("comida-caseira")
    if _sim(tags, "diet:vegetarian") or _sim(tags, "diet:vegan") or cozinha & {"vegetarian", "vegan"}:
        slugs.add("vegetariano")
    if _sim(tags, "wheelchair"):
        slugs.add("acessivel")
    if _sim(tags, "dog"):
        slugs.add("aceita-pet")
    if _sim(tags, "live_music"):
        slugs.add("musica-ao-vivo")
    if _sim(tags, "outdoor_seating"):
        slugs.add("ao-ar-livre")
    return slugs


def endereco(tags):
    rua = tags.get("addr:street", "").strip()
    numero = tags.get("addr:housenumber", "").strip()
    if not rua:
        return ""
    return f"{rua}, {numero}" if numero else rua


def distancia_km(a, b):
    """Haversine entre dois Point (lng, lat)."""
    lng1, lat1, lng2, lat2 = map(math.radians, (a.x, a.y, b.x, b.y))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def cidade_mais_proxima(ponto, cidades, limite_km=20):
    melhor = min(cidades, key=lambda c: distancia_km(ponto, c.ponto), default=None)
    if melhor and distancia_km(ponto, melhor.ponto) <= limite_km:
        return melhor
    return None


def ler_geojsonseq(caminho):
    """Lê a saída do `osmium export -f geojsonseq` (uma feature por linha, com ou sem separador RS)."""
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip().lstrip("\x1e")
            if linha:
                yield json.loads(linha)


def _ponto(geometria):
    geom = GEOSGeometry(json.dumps(geometria), srid=4326)
    ponto = geom if geom.geom_type == "Point" else geom.point_on_surface
    return Point(round(ponto.x, 7), round(ponto.y, 7), srid=4326)


def _campos_opl(linha):
    """Uma linha OPL -> (tipo+id, {campo: valor}), ex.: ("r123", {"T": "...", "M": "...", "x": "..."})."""
    partes = linha.strip().split(" ")
    return partes[0], {c[0]: c[1:] for c in partes[1:] if c}


def _tags_opl(texto):
    return {_desescapar_opl(k): _desescapar_opl(v) for k, v in (par.split("=", 1) for par in texto.split(",") if "=" in par)}


def _desescapar_opl(texto):
    # OPL escreve caracteres especiais como %hex%, ex.: "S%20%o" -> espaço.
    partes = texto.split("%")
    saida = partes[0]
    for i in range(1, len(partes), 2):
        codigo = partes[i]
        saida += chr(int(codigo, 16)) if codigo else "%"
        if i + 1 < len(partes):
            saida += partes[i + 1]
    return saida


def ler_municipios_opl(caminho, prefixo_ibge="43"):
    """Municípios (relações admin_level=8) de uma UF, pelo prefixo do código IBGE (43 = RS).
    Retorna {id do nó da sede: {"nome", "ibge"}}. A sede vem do membro com papel admin_centre."""
    municipios = {}
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in arquivo:
            if not linha.startswith("r"):
                continue
            _, campos = _campos_opl(linha)
            tags = _tags_opl(campos.get("T", ""))
            ibge = tags.get("IBGE:GEOCODIGO", "")
            if not ibge.startswith(prefixo_ibge) or "name" not in tags:
                continue
            for membro in campos.get("M", "").split(","):
                if membro.endswith("@admin_centre") and membro.startswith("n"):
                    municipios[membro[1:].split("@")[0]] = {"nome": tags["name"], "ibge": ibge}
                    break
    return municipios


def ler_nos_opl(caminho):
    """{id: (lng, lat)} dos nós de um arquivo OPL."""
    nos = {}
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in arquivo:
            if linha.startswith("n"):
                ident, campos = _campos_opl(linha)
                if campos.get("x") and campos.get("y"):
                    nos[ident[1:]] = (float(campos["x"]), float(campos["y"]))
    return nos


def _id(propriedades):
    return f"{propriedades.get('@type')}/{propriedades.get('@id')}"


# Relação do estado no OSM, usada como contorno do recorte. 242620 = Rio Grande do Sul.
RELACAO_RS = 242620


def extrair_pbf(pbf, bbox=BBOX_VALE, pasta=None, relacao=None):
    """Recorta a região, filtra as categorias e exporta GeoJSON. Retorna o caminho do .geojsonseq.

    Com `relacao`, recorta pelo contorno dessa relação (ex.: o estado) em vez da caixa `bbox`."""
    pasta = Path(pasta or tempfile.mkdtemp(prefix="osm-"))
    recorte, filtrado, saida = pasta / "recorte.osm.pbf", pasta / "filtrado.osm.pbf", pasta / "lugares.geojsonseq"
    contorno = pasta / "contorno.osm.pbf"

    por_chave = {}
    for categoria in CATEGORIAS:
        chave, valor = categoria.split("=", 1)
        por_chave.setdefault(chave, []).append(valor)
    filtros = [f"nwr/{chave}={','.join(valores)}" for chave, valores in por_chave.items()]

    if relacao:
        # o contorno é a própria relação do estado, com os caminhos e nós que a formam
        subprocess.run(["osmium", "getid", "-r", str(pbf), f"r{relacao}", "-o", str(contorno), "--overwrite"],
                       check=True, capture_output=True, text=True)
        corte = ["-p", str(contorno)]
    else:
        corte = ["-b", ",".join(str(v) for v in bbox)]
    passos = [
        ["osmium", "extract", *corte, "-s", "smart", str(pbf), "-o", str(recorte), "--overwrite"],
        ["osmium", "tags-filter", str(recorte), *filtros, "-o", str(filtrado), "--overwrite"],
        ["osmium", "export", str(filtrado), "-f", "geojsonseq", "-a", "type,id",
         "--geometry-types=point,polygon", "-o", str(saida), "--overwrite"],
    ]
    for comando in passos:
        subprocess.run(comando, check=True, capture_output=True, text=True)
    return saida


def extrair_municipios(pbf, prefixo_ibge="43", pasta=None):
    """Municípios de uma UF com a posição da sede. Retorna lista de {nome, ibge, no, lng, lat}."""
    pasta = Path(pasta or tempfile.mkdtemp(prefix="osm-"))
    relacoes, ids, nos = pasta / "municipios.opl", pasta / "sedes.txt", pasta / "sedes.opl"
    subprocess.run(["osmium", "tags-filter", str(pbf), "r/admin_level=8", "-R", "-f", "opl", "-o", str(relacoes),
                    "--overwrite"], check=True, capture_output=True, text=True)
    municipios = ler_municipios_opl(relacoes, prefixo_ibge)
    ids.write_text("".join(f"n{no}\n" for no in municipios))
    subprocess.run(["osmium", "getid", str(pbf), "-i", str(ids), "-f", "opl", "-o", str(nos), "--overwrite"],
                   check=True, capture_output=True, text=True)
    posicoes = ler_nos_opl(nos)
    return [{**dados, "no": no, "lng": posicoes[no][0], "lat": posicoes[no][1]}
            for no, dados in municipios.items() if no in posicoes]


@transaction.atomic
def importar_municipios(municipios):
    """Grava as cidades (sedes de município). Pode rodar de novo: atualiza pelo id do nó da sede."""
    novas = 0
    for m in municipios:
        _, criada = Cidade.objects.update_or_create(
            id_externo=f"node/{m['no']}",
            defaults={"nome": m["nome"][:120], "codigo_ibge": m["ibge"],
                      "ponto": Point(round(m["lng"], 7), round(m["lat"], 7), srid=4326)},
        )
        novas += criada
    return {"cidades": len(municipios), "novas": novas}


@transaction.atomic
def importar(features, progresso=None):
    """Grava os lugares numa transação só (tudo ou nada). Pode rodar de novo: atualiza pelo id do OSM.
    A cidade de cada lugar vem do addr:city ou da sede de município mais próxima (importar_cidades antes)."""
    resumo = {"lugares_novos": 0, "lugares_atualizados": 0, "ignorados": 0}
    cidades = list(Cidade.objects.all())
    tags_por_slug = {t.slug: t for t in Tag.objects.all()}

    for n, f in enumerate(features, 1):
        if progresso and n % 5000 == 0:
            progresso(n)
        tags = f.get("properties", {})
        categoria = classificar(tags)
        nome = (tags.get("name") or "").strip()
        if not categoria or not nome or not f.get("geometry"):
            resumo["ignorados"] += 1
            continue

        ponto = _ponto(f["geometry"])
        proxima = cidade_mais_proxima(ponto, cidades)
        lugar, criado = Lugar.objects.update_or_create(
            fonte=Lugar.Fonte.OSM,
            id_externo=_id(tags),
            defaults={
                "nome": nome[:200],
                "ponto": ponto,
                "categoria": categoria,
                "endereco": endereco(tags)[:300],
                "cidade": (tags.get("addr:city") or (proxima.nome if proxima else ""))[:120],
                "aproximado": False,
            },
        )
        lugar.tags.set([tags_por_slug[s] for s in tags_iniciais(tags, categoria) if s in tags_por_slug])
        resumo["lugares_novos" if criado else "lugares_atualizados"] += 1

    return resumo
