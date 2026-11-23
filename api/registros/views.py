import datetime
import unicodedata

from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import Q
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from lugares.models import Cidade, Tag
from lugares.osm import nome_da_categoria
from lugares.serializers import LugarSerializer
from salvos.models import Salvo

from .models import Ocasiao, PesoGosto, PreferenciaDeclarada, Registro
from .comunidade import recalcular_motivos
from .perfil import recalcular_perfil
from .serializers import RegistroSerializer
from .sugestoes import TIPOS, origem_da_busca, sugerir


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def registros_de(usuario):
    return (
        Registro.objects.filter(usuario=usuario)
        .select_related("lugar")
        .prefetch_related("tags", "lugar__tags", "lugar__motivos_comunidade__tag")
        .order_by("-visitado_em", "-criado_em")
    )


class RegistrosView(generics.ListCreateAPIView):
    """Visitas da pessoa. ?q= busca no motivo (marcado ou escrito), no lugar e na cidade; ?lugar= filtra."""

    serializer_class = RegistroSerializer

    def get_queryset(self):
        registros = registros_de(self.request.user)
        q = sem_acento(self.request.query_params.get("q", "").strip())[:100]
        if q:
            registros = registros.filter(
                Q(tags__nome__unaccent__icontains=q)
                | Q(tags__slug__icontains=q.replace(" ", "-"))
                | Q(motivo__unaccent__icontains=q)
                | Q(lugar__nome__unaccent__icontains=q)
                | Q(lugar__cidade__unaccent__icontains=q)
            ).distinct()
        lugar = self.request.query_params.get("lugar")
        if lugar and lugar.isdigit():
            registros = registros.filter(lugar_id=int(lugar))
        return registros

    def perform_create(self, serializer):
        registro = serializer.save(usuario=self.request.user)
        recalcular_perfil(self.request.user)
        recalcular_motivos([registro.lugar_id])


class RegistroView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RegistroSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return registros_de(self.request.user)

    def perform_update(self, serializer):
        lugar_antes = serializer.instance.lugar_id
        registro = serializer.save()
        recalcular_perfil(self.request.user)
        recalcular_motivos([lugar_antes, registro.lugar_id])

    def perform_destroy(self, instance):
        lugar = instance.lugar_id
        instance.delete()
        recalcular_perfil(self.request.user)
        recalcular_motivos([lugar])


class SugestoesView(APIView):
    """GET /api/sugestoes/?lat=&lng= | ?cidade_id= &ocasiao= &quando=AAAA-MM-DD &hora=HH:MM &tipo=bar|lanche|restaurante|cafe|noite|passeio

    Sem lat/lng nem cidade, procura na cidade da pessoa ou perto da última visita."""

    def get(self, request):
        params = request.query_params
        ocasiao = params.get("ocasiao", "")
        if ocasiao and ocasiao not in Ocasiao.values:
            return Response({"ocasiao": ["Ocasião desconhecida."]}, status=status.HTTP_400_BAD_REQUEST)

        ponto = None
        try:
            lat, lng = float(params["lat"]), float(params["lng"])
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                ponto = Point(lng, lat, srid=4326)
        except (KeyError, ValueError):
            pass
        cidade = None
        if params.get("cidade_id", "").isdigit():
            cidade = Cidade.objects.filter(pk=int(params["cidade_id"])).first()

        tipo = params.get("tipo", "")
        if tipo and tipo not in TIPOS:
            return Response({"tipo": ["Tipo de lugar desconhecido."]}, status=status.HTTP_400_BAD_REQUEST)
        quando, hora = None, None
        if params.get("quando"):
            try:
                quando = datetime.date.fromisoformat(params["quando"])
            except ValueError:
                return Response({"quando": ["Use a data no formato AAAA-MM-DD."]}, status=status.HTTP_400_BAD_REQUEST)
        if params.get("hora"):
            try:
                hh, mm = params["hora"].split(":")
                hora = int(hh) * 60 + int(mm)
                assert quando and 0 <= int(hh) < 24 and 0 <= int(mm) < 60
            except (ValueError, AssertionError):
                return Response({"hora": ["Use a hora como HH:MM, junto com a data."]}, status=status.HTTP_400_BAD_REQUEST)

        origem = origem_da_busca(request.user, ponto, cidade)
        resultados = sugerir(request.user, origem, ocasiao, quando=quando, hora=hora, tipo=tipo)
        tem_gosto = (
            PesoGosto.objects.filter(usuario=request.user, peso__gt=0).exists()
            or PreferenciaDeclarada.objects.filter(usuario=request.user).exists()
        )
        return Response({
            "origem": None if origem is None else {
                "tipo": origem["tipo"], "nome": origem["nome"], "cidade_id": origem.get("cidade_id"),
            },
            "tem_gosto": tem_gosto,
            "resultados": [
                {
                    "lugar": LugarSerializer(r["lugar"]).data,
                    "pontos": r["pontos"],
                    "combina": r["combina"],
                    "comunidade": r["comunidade"],
                    "salvo": r["salvo"],
                    "horario": r["horario"],
                }
                for r in resultados
            ],
        })


class PreferenciasSerializer(serializers.Serializer):
    tags = serializers.SlugRelatedField(many=True, slug_field="slug", queryset=Tag.objects.all())

    def validate_tags(self, tags):
        if len(tags) > 15:
            raise serializers.ValidationError("Escolha até 15.")
        return tags


class PreferenciasView(APIView):
    """Os gostos que a pessoa escolhe antes (ou além) das visitas. PUT substitui a lista toda."""

    def get(self, request):
        slugs = PreferenciaDeclarada.objects.filter(usuario=request.user).values_list("tag__slug", flat=True)
        return Response({"tags": sorted(slugs)})

    def put(self, request):
        entrada = PreferenciasSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        with transaction.atomic():
            PreferenciaDeclarada.objects.filter(usuario=request.user).delete()
            PreferenciaDeclarada.objects.bulk_create(
                PreferenciaDeclarada(usuario=request.user, tag=tag) for tag in set(entrada.validated_data["tags"])
            )
        return self.get(request)


class MapaView(APIView):
    """Os lugares da pessoa em GeoJSON: os que ela quer conhecer e os que já visitou.

    Um lugar salvo e visitado aparece uma vez só, como visitado."""

    def get(self, request):
        lugares = {}

        def item(lugar):
            return lugares.setdefault(lugar.id, {
                "lugar": lugar, "salvo_id": None, "visita_id": None, "visitas": 0, "nota": None,
            })

        for salvo in Salvo.objects.filter(usuario=request.user, lugar__isnull=False).select_related("lugar"):
            item(salvo.lugar)["salvo_id"] = salvo.id
        for registro in (
            Registro.objects.filter(usuario=request.user).select_related("lugar").order_by("visitado_em", "id")
        ):
            dados = item(registro.lugar)
            dados["visitas"] += 1
            dados["visita_id"] = registro.id  # a mais recente fica por último
            dados["nota"] = registro.nota

        features = []
        for dados in lugares.values():
            lugar = dados["lugar"]
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lugar.ponto.x, lugar.ponto.y]},
                "properties": {
                    "lugar_id": lugar.id,
                    "nome": lugar.nome,
                    "categoria": lugar.categoria,
                    "categoria_nome": nome_da_categoria(lugar.categoria),
                    "cidade": lugar.cidade,
                    "tipo": "visitado" if dados["visitas"] else "salvo",
                    "salvo_id": dados["salvo_id"],
                    "visita_id": dados["visita_id"],
                    "visitas": dados["visitas"],
                    "nota": dados["nota"],
                },
            })
        return Response({"type": "FeatureCollection", "features": features})
