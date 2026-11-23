from rest_framework import serializers

from lugares.serializers import LugarSerializer
from registros.models import Registro


def pessoa(usuario):
    """O que uma pessoa vê da outra: nome e iniciais. Nunca e-mail."""
    partes = [p for p in usuario.nome.split() if p]
    return {"id": usuario.id, "nome": usuario.nome, "iniciais": "".join(p[0].upper() for p in partes[:2])}


class VisitaCompartilhadaSerializer(serializers.ModelSerializer):
    lugar = LugarSerializer(read_only=True)
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field="slug")

    class Meta:
        model = Registro
        fields = ["id", "lugar", "visitado_em", "ocasiao", "nota", "tags", "motivo"]
