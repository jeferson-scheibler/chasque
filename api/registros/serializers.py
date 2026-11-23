import datetime

from django.utils import timezone
from rest_framework import serializers

from lugares.models import Lugar, Tag
from lugares.serializers import LugarSerializer

from .models import Registro

MAX_MOTIVOS = 10


class RegistroSerializer(serializers.ModelSerializer):
    lugar = LugarSerializer(read_only=True)
    lugar_id = serializers.PrimaryKeyRelatedField(source="lugar", queryset=Lugar.objects.all(), write_only=True)
    tags = serializers.SlugRelatedField(many=True, slug_field="slug", queryset=Tag.objects.all(), required=False)

    class Meta:
        model = Registro
        fields = ["id", "lugar", "lugar_id", "visitado_em", "ocasiao", "nota", "tags", "motivo", "privado", "criado_em"]
        read_only_fields = ["id", "criado_em"]
        extra_kwargs = {"motivo": {"required": False, "allow_blank": True, "max_length": 500}}

    def validate_visitado_em(self, data):
        if data > timezone.localdate():
            raise serializers.ValidationError("A data da visita não pode ser no futuro.")
        if data < datetime.date(1950, 1, 1):
            raise serializers.ValidationError("Confira a data da visita.")
        return data

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
        return attrs
