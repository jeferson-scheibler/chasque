from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from .busca import por_nome, sem_acento
from .models import Cidade, Lugar, Tag
from .osm import cidade_mais_proxima
from .serializers import CidadeSerializer, CriarLugarSerializer, LugarSerializer, TagSerializer

LIMITE_RESULTADOS = 20
RAIO_DUPLICADO_M = 200


def ponto_da_query(params):
    try:
        lat, lng = float(params["lat"]), float(params["lng"])
    except (KeyError, TypeError, ValueError):
        return None
    if -90 <= lat <= 90 and -180 <= lng <= 180:
        return Point(lng, lat, srid=4326)
    return None


class LugarView(generics.RetrieveAPIView):
    serializer_class = LugarSerializer
    queryset = Lugar.objects.prefetch_related("tags", "motivos_comunidade__tag")


class TagsView(generics.ListAPIView):
    """Motivos para marcar numa visita, agrupados (ambiente, preço, comida, serviço, experiência)."""

    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    pagination_class = None


class CidadesView(generics.ListAPIView):
    serializer_class = CidadeSerializer
    queryset = Cidade.objects.all()
    pagination_class = None


class LugaresView(APIView):
    """GET: busca por nome (sem acento, tolera erro de digitação) e/ou proximidade.
    POST: cria um lugar que não está na base."""

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "criar_lugar"
            return [ScopedRateThrottle()]
        return [UserRateThrottle()]

    def get(self, request):
        q = sem_acento(request.query_params.get("q", "").strip())[:100]
        perto = ponto_da_query(request.query_params)
        lugares = Lugar.objects.prefetch_related("tags", "motivos_comunidade__tag")

        if not q and not perto:
            return Response({"q": ["Informe o que buscar ou a sua posição."]}, status=status.HTTP_400_BAD_REQUEST)

        ordem = []
        if q:
            lugares = por_nome(lugares, q)
            ordem.append("-semelhanca")
        if perto:
            lugares = lugares.annotate(distancia=Distance("ponto", perto))
            ordem.append("distancia")
        ordem.append("nome")

        resultado = lugares.order_by(*ordem)[:LIMITE_RESULTADOS]
        return Response(LugarSerializer(resultado, many=True).data)

    def post(self, request):
        entrada = CriarLugarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data
        cidade = dados.get("cidade_id")

        if "lat" in dados:
            ponto, aproximado = Point(dados["lng"], dados["lat"], srid=4326), False
            if cidade is None:
                cidade = cidade_mais_proxima(ponto, list(Cidade.objects.all()))
        else:
            ponto, aproximado = cidade.ponto, True

        # Mesmo nome a menos de 200 m: é o mesmo lugar.
        existente = (
            Lugar.objects.filter(ponto__dwithin=(ponto, D(m=RAIO_DUPLICADO_M)))
            .filter(nome__unaccent__iexact=dados["nome"].strip())
            .first()
        )
        if existente:
            return Response(LugarSerializer(existente).data, status=status.HTTP_200_OK)

        lugar = Lugar.objects.create(
            nome=dados["nome"].strip(),
            endereco=dados.get("endereco", "").strip(),
            ponto=ponto,
            aproximado=aproximado,
            cidade=cidade.nome if cidade else "",
            fonte=Lugar.Fonte.USUARIO,
            criado_por=request.user,
        )
        return Response(LugarSerializer(lugar).data, status=status.HTTP_201_CREATED)
