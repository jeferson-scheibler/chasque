from rest_framework import serializers

from lugares.models import Lugar, Tag
from lugares.serializers import LugarSerializer

from .models import Intencao, Salvo


class SalvoSerializer(serializers.ModelSerializer):
    lugar = LugarSerializer(read_only=True)
    lugar_id = serializers.PrimaryKeyRelatedField(
        source="lugar", queryset=Lugar.objects.all(), allow_null=True, required=False, write_only=True
    )

    visitado = serializers.SerializerMethodField()
    intencao = serializers.SerializerMethodField()

    class Meta:
        model = Salvo
        fields = [
            "id", "origem", "url", "tipo", "perfil", "texto", "lugar", "lugar_id", "visitado", "intencao", "criado_em",
        ]
        read_only_fields = ["id", "origem", "url", "tipo", "perfil", "criado_em"]

    def get_visitado(self, salvo):
        """Se a pessoa já registrou uma visita ao lugar deste link (anotado pela view)."""
        return bool(getattr(salvo, "visitado", False))

    def get_intencao(self, salvo):
        """Por que a pessoa salvou, lido pela IA ou confirmado por ela. None se não há ou se não deu para ler."""
        try:
            intencao = salvo.intencao
        except Intencao.DoesNotExist:
            return None
        if intencao.estado == Intencao.Estado.FALHOU:
            return None
        sugerido = intencao.lugar_sugerido if not salvo.lugar_id else None
        return {
            "estado": intencao.estado,
            "frase": intencao.frase,
            "tags": [t.slug for t in intencao.tags.all()],
            "lugar_sugerido": LugarSerializer(sugerido).data if sugerido else None,
        }


class CompartilhamentoSerializer(serializers.Serializer):
    """O que chega do compartilhamento do celular (Web Share Target / intent do Android / extensão do iOS)."""

    url = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    text = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    title = serializers.CharField(required=False, allow_blank=True, max_length=500)
    lugar_id = serializers.PrimaryKeyRelatedField(queryset=Lugar.objects.all(), required=False, allow_null=True)


class IntencaoSerializer(serializers.Serializer):
    """O que a pessoa confirma ou corrige na intenção. Frase e motivos vazios querem dizer "não é isso"."""

    frase = serializers.CharField(max_length=120, allow_blank=True, trim_whitespace=True)
    tags = serializers.ListField(child=serializers.SlugField(max_length=40), max_length=3, allow_empty=True)

    def validate_tags(self, slugs):
        unicos = list(dict.fromkeys(slugs))
        existentes = set(Tag.objects.filter(slug__in=unicos).values_list("slug", flat=True))
        desconhecidos = [s for s in unicos if s not in existentes]
        if desconhecidos:
            raise serializers.ValidationError(f"Motivo desconhecido: {', '.join(desconhecidos)}.")
        return unicos
