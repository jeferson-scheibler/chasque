import unicodedata

from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import Q
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from lugares.models import Cidade, Tag
from lugares.serializers import LugarSerializer

from .models import Ocasiao, PesoGosto, PreferenciaDeclarada, Registro
from .perfil import recalcular_perfil
from .serializers import RegistroSerializer
from .sugestoes import origem_da_busca, sugerir


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def registros_de(usuario):
    return (
        Registro.objects.filter(usuario=usuario)
        .select_related("lugar")
        .prefetch_related("tags", "lugar__tags")
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
        serializer.save(usuario=self.request.user)
        recalcular_perfil(self.request.user)


class RegistroView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RegistroSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return registros_de(self.request.user)

    def perform_update(self, serializer):
        serializer.save()
        recalcular_perfil(self.request.user)

    def perform_destroy(self, instance):
        instance.delete()
        recalcular_perfil(self.request.user)


class SugestoesView(APIView):
    """GET /api/sugestoes/?lat=&lng= | ?cidade_id= &ocasiao=

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

        origem = origem_da_busca(request.user, ponto, cidade)
        resultados = sugerir(request.user, origem, ocasiao)
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
                    "salvo": r["salvo"],
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
