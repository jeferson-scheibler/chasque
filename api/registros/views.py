import unicodedata

from django.db.models import Q
from rest_framework import generics

from .models import Registro
from .perfil import recalcular_perfil
from .serializers import RegistroSerializer


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
