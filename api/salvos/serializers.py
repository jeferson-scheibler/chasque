from rest_framework import serializers

from lugares.models import Lugar
from lugares.serializers import LugarSerializer

from .models import Salvo


class SalvoSerializer(serializers.ModelSerializer):
    lugar = LugarSerializer(read_only=True)
    lugar_id = serializers.PrimaryKeyRelatedField(
        source="lugar", queryset=Lugar.objects.all(), allow_null=True, required=False, write_only=True
    )

    visitado = serializers.SerializerMethodField()

    class Meta:
        model = Salvo
        fields = ["id", "origem", "url", "tipo", "perfil", "texto", "lugar", "lugar_id", "visitado", "criado_em"]
        read_only_fields = ["id", "origem", "url", "tipo", "perfil", "criado_em"]

    def get_visitado(self, salvo):
        """Se a pessoa já registrou uma visita ao lugar deste link (anotado pela view)."""
        return bool(getattr(salvo, "visitado", False))


class CompartilhamentoSerializer(serializers.Serializer):
    """O que chega do compartilhamento do celular (Web Share Target / intent do Android / extensão do iOS)."""

    url = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    text = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    title = serializers.CharField(required=False, allow_blank=True, max_length=500)
