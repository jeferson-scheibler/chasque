from urllib.parse import urlsplit

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import ical, push
from .models import Agenda, InscricaoPush, Roteiro
from .planejar import ler
from .serializers import AgendaSerializer, RoteiroSerializer


class AgendaEntrada(serializers.Serializer):
    url = serializers.CharField(max_length=2000)


class AgendaView(APIView):
    """GET: situação da agenda. PUT {url}: liga (e lê na hora). DELETE: desliga e apaga os roteiros futuros."""

    throttle_scope = "agenda"

    def get_throttles(self):
        # só ligar a agenda (que faz o servidor baixar um endereço) tem limite próprio
        return [ScopedRateThrottle()] if self.request.method == "PUT" else super().get_throttles()

    def get(self, request):
        agenda = Agenda.objects.filter(usuario=request.user).first()
        if agenda is None:
            return Response({"conectada": False})
        return Response({"conectada": True, **AgendaSerializer(agenda).data})

    def put(self, request):
        entrada = AgendaEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            url = ical.normalizar(entrada.validated_data["url"])
        except ical.AgendaInvalida as erro:
            return Response({"url": [str(erro)]}, status=status.HTTP_400_BAD_REQUEST)
        agenda = Agenda.objects.filter(usuario=request.user).first() or Agenda(usuario=request.user)
        agenda.url, agenda.servico = url, (urlsplit(url).hostname or "")[:120]
        try:
            with transaction.atomic():  # o endereço novo não abriu: fica o que já funcionava
                ler(agenda)
        except ical.AgendaInvalida as erro:
            return Response({"url": [str(erro)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"conectada": True, **AgendaSerializer(agenda).data})

    def delete(self, request):
        Agenda.objects.filter(usuario=request.user).delete()
        Roteiro.objects.filter(usuario=request.user, dia__gt=timezone.localdate(), dispensado_em__isnull=True).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LerAgendaView(APIView):
    """POST: lê a agenda de novo agora."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "agenda"

    def post(self, request):
        agenda = Agenda.objects.filter(usuario=request.user).first()
        if agenda is None:
            return Response({"detail": "Nenhuma agenda ligada."}, status=status.HTTP_404_NOT_FOUND)
        try:
            ler(agenda)
        except ical.AgendaInvalida:
            pass  # o erro fica guardado e volta na resposta
        return Response({"conectada": True, **AgendaSerializer(agenda).data})


def roteiros_da_pessoa(usuario):
    return (
        Roteiro.objects.filter(usuario=usuario, dia__gte=timezone.localdate(), dispensado_em__isnull=True)
        .prefetch_related("paradas__lugar__tags", "paradas__lugar__motivos_comunidade__tag")
    )


class RoteirosView(generics.ListAPIView):
    """Roteiros dos próximos fins de semana livres."""

    serializer_class = RoteiroSerializer
    pagination_class = None

    def get_queryset(self):
        return roteiros_da_pessoa(self.request.user)


class RoteiroView(generics.RetrieveDestroyAPIView):
    """GET: um roteiro (marca como visto). DELETE: "agora não", some e não volta para esse dia."""

    serializer_class = RoteiroSerializer

    def get_queryset(self):
        return roteiros_da_pessoa(self.request.user)

    def retrieve(self, request, *args, **kwargs):
        roteiro = self.get_object()
        if roteiro.visto_em is None:
            roteiro.visto_em = timezone.now()
            roteiro.save(update_fields=["visto_em"])
        return Response(self.get_serializer(roteiro).data)

    def perform_destroy(self, roteiro):
        roteiro.dispensado_em = timezone.now()
        roteiro.save(update_fields=["dispensado_em"])


class InscricaoEntrada(serializers.Serializer):
    endpoint = serializers.URLField(max_length=1000)
    p256dh = serializers.CharField(max_length=200)
    auth = serializers.CharField(max_length=100)

    def validate_endpoint(self, valor):
        if not push.endpoint_valido(valor):
            raise serializers.ValidationError("Serviço de avisos desconhecido.")
        return valor


class AvisosView(APIView):
    """GET: chave pública do Web Push. POST: guarda a inscrição do aparelho. DELETE {endpoint}: tira."""

    def get(self, request):
        return Response({
            "chave": settings.VAPID_PUBLICA if push.configurado() else "",
            "aparelhos": InscricaoPush.objects.filter(usuario=request.user).count(),
        })

    def post(self, request):
        entrada = InscricaoEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data
        # o mesmo aparelho pode trocar de conta: a inscrição vai para quem está logado agora
        InscricaoPush.objects.update_or_create(
            endpoint=dados["endpoint"],
            defaults={"usuario": request.user, "p256dh": dados["p256dh"], "auth": dados["auth"]},
        )
        return Response(status=status.HTTP_201_CREATED)

    def delete(self, request):
        InscricaoPush.objects.filter(usuario=request.user, endpoint=request.data.get("endpoint", "")).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AvisoTesteView(APIView):
    """POST: manda um aviso de teste para os aparelhos da própria pessoa."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "aviso_teste"

    def post(self, request):
        enviados = push.enviar(request.user, "Chasque", "Os avisos estão ligados neste aparelho.",
                               "/abas/conta/agenda", "teste")
        return Response({"enviados": enviados})
