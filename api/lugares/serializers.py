from rest_framework import serializers

from .models import Cidade, Lugar
from .osm import nome_da_categoria


class CidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cidade
        fields = ["id", "nome"]


class LugarSerializer(serializers.ModelSerializer):
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    categoria_nome = serializers.SerializerMethodField()
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field="slug")
    distancia_m = serializers.SerializerMethodField()

    class Meta:
        model = Lugar
        fields = [
            "id", "nome", "endereco", "cidade", "categoria", "categoria_nome",
            "lat", "lng", "aproximado", "fonte", "tags", "distancia_m",
        ]

    def get_lat(self, lugar):
        return lugar.ponto.y

    def get_lng(self, lugar):
        return lugar.ponto.x

    def get_categoria_nome(self, lugar):
        return nome_da_categoria(lugar.categoria)

    def get_distancia_m(self, lugar):
        distancia = getattr(lugar, "distancia", None)
        return round(distancia.m) if distancia is not None else None


class CriarLugarSerializer(serializers.Serializer):
    """Lugar que a pessoa não achou na base. Precisa de posição exata ou de uma cidade."""

    nome = serializers.CharField(min_length=2, max_length=200)
    cidade_id = serializers.PrimaryKeyRelatedField(queryset=Cidade.objects.all(), required=False, allow_null=True)
    lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    lng = serializers.FloatField(required=False, min_value=-180, max_value=180)
    endereco = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate(self, attrs):
        tem_ponto = "lat" in attrs and "lng" in attrs
        if not tem_ponto and not attrs.get("cidade_id"):
            raise serializers.ValidationError("Informe a cidade ou use a sua localização atual.")
        if ("lat" in attrs) != ("lng" in attrs):
            raise serializers.ValidationError("Latitude e longitude vão juntas.")
        return attrs
