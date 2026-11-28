import datetime

from django.utils import timezone
from rest_framework import serializers

from lugares.models import Lugar, Tag
from lugares.serializers import LugarSerializer

from salvos.models import Intencao

from .models import Registro

MAX_MOTIVOS = 10


class RegistroSerializer(serializers.ModelSerializer):
    lugar = LugarSerializer(read_only=True)
    lugar_id = serializers.PrimaryKeyRelatedField(source="lugar", queryset=Lugar.objects.all(), write_only=True)
    tags = serializers.SlugRelatedField(many=True, slug_field="slug", queryset=Tag.objects.all(), required=False)
    intencao_id = serializers.PrimaryKeyRelatedField(
        source="intencao", queryset=Intencao.objects.all(), allow_null=True, required=False
    )
    intencao = serializers.SerializerMethodField()

    class Meta:
        model = Registro
        fields = [
            "id", "lugar", "lugar_id", "visitado_em", "ocasiao", "nota", "tags", "motivo", "privado",
            "intencao_id", "intencao", "expectativa", "criado_em",
        ]
        read_only_fields = ["id", "criado_em"]
        extra_kwargs = {"motivo": {"required": False, "allow_blank": True, "max_length": 500}}

    def validate_visitado_em(self, data):
        if data > timezone.localdate():
            raise serializers.ValidationError("A data da visita não pode ser no futuro.")
        if data < datetime.date(1950, 1, 1):
            raise serializers.ValidationError("Confira a data da visita.")
        return data

    def get_intencao(self, registro):
        """O motivo de ter salvo, para a tela perguntar de novo se valeu ao editar a visita."""
        intencao = registro.intencao
        if intencao is None:
            return None
        return {"frase": intencao.frase, "tags": [t.slug for t in intencao.tags.all()]}

    def validate_intencao_id(self, intencao):
        pedido = self.context.get("request")
        if intencao is not None and (pedido is None or intencao.salvo.usuario_id != pedido.user.id):
            raise serializers.ValidationError("Motivo não encontrado.")
        return intencao

    def validate_tags(self, tags):
        if len(tags) > MAX_MOTIVOS:
            raise serializers.ValidationError(f"Escolha até {MAX_MOTIVOS} motivos.")
        return tags

    def validate(self, attrs):
        # O Chasque existe para guardar o porquê: pelo menos um motivo marcado ou escrito.
        tags = attrs.get("tags", None if self.instance is None else list(self.instance.tags.all()))
        motivo = attrs.get("motivo", "" if self.instance is None else self.instance.motivo)
        if not tags and not (motivo or "").strip():
            raise serializers.ValidationError({"tags": ["Marque pelo menos um motivo ou escreva por que foi assim."]})
        intencao = attrs.get("intencao", None if self.instance is None else self.instance.intencao)
        if attrs.get("expectativa") and intencao is None:
            raise serializers.ValidationError({"expectativa": ["Só dá para dizer se valeu quando há um motivo."]})
        if "intencao" in attrs and intencao is None:
            attrs["expectativa"] = ""  # sem motivo, não há o que valer
        return attrs
