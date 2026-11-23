from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from contas.models import Usuario
from registros.models import Ocasiao, Registro

from .models import Confianca, Convite, novo_codigo
from .serializers import VisitaCompartilhadaSerializer, pessoa


def visitas_compartilhadas(usuario):
    return Registro.objects.filter(usuario=usuario, privado=False)


class PessoasView(APIView):
    """Tudo da tela Pessoas: meu convite, pedidos recebidos e enviados, quem eu sigo e quem me segue."""

    def get(self, request):
        eu = request.user
        recebidas = Confianca.objects.filter(seguido=eu).select_related("seguidor")
        dadas = (
            Confianca.objects.filter(seguidor=eu)
            .select_related("seguido")
            .annotate(compartilhadas=Count("seguido__registros", filter=Q(seguido__registros__privado=False)))
        )
        return Response({
            "convite": Convite.de(eu).codigo,
            "pedidos": [{"id": c.id, "pessoa": pessoa(c.seguidor)} for c in recebidas if c.estado == "pendente"],
            "seguidores": [{"id": c.id, "pessoa": pessoa(c.seguidor)} for c in recebidas if c.estado == "aceito"],
            "enviados": [{"id": c.id, "pessoa": pessoa(c.seguido)} for c in dadas if c.estado == "pendente"],
            "seguindo": [
                {"id": c.id, "pessoa": pessoa(c.seguido), "visitas": c.compartilhadas} for c in dadas if c.estado == "aceito"
            ],
        })


class NovoConviteView(APIView):
    """Troca o código do link: quem tinha o antigo não consegue mais pedir para seguir."""

    def post(self, request):
        convite = Convite.de(request.user)
        convite.codigo = novo_codigo()
        convite.save(update_fields=["codigo", "criado_em"])
        return Response({"convite": convite.codigo})


class ConviteView(APIView):
    """GET mostra de quem é o convite; POST pede para seguir essa pessoa."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "convite"

    def dono(self, codigo):
        return get_object_or_404(Convite.objects.select_related("usuario"), codigo=codigo, usuario__is_active=True).usuario

    def estado(self, eu, dono):
        if eu == dono:
            return "proprio"
        conf = Confianca.objects.filter(seguidor=eu, seguido=dono).first()
        return conf.estado if conf else None

    def get(self, request, codigo):
        dono = self.dono(codigo)
        return Response({"pessoa": pessoa(dono), "estado": self.estado(request.user, dono)})

    def post(self, request, codigo):
        dono = self.dono(codigo)
        if dono == request.user:
            return Response({"detail": "Esse é o seu próprio convite."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                Confianca.objects.get_or_create(seguidor=request.user, seguido=dono)
        except IntegrityError:
            pass
        return Response({"pessoa": pessoa(dono), "estado": self.estado(request.user, dono)}, status=status.HTTP_201_CREATED)


class AceitarView(APIView):
    def post(self, request, pk):
        conf = get_object_or_404(Confianca, pk=pk, seguido=request.user, estado=Confianca.Estado.PENDENTE)
        conf.estado = Confianca.Estado.ACEITO
        conf.aceito_em = timezone.now()
        conf.save(update_fields=["estado", "aceito_em"])
        return Response({"id": conf.id, "pessoa": pessoa(conf.seguidor)})


class ConfiancaView(APIView):
    """DELETE serve para recusar pedido, cancelar pedido, deixar de seguir e remover seguidor."""

    def delete(self, request, pk):
        conf = get_object_or_404(Confianca, Q(seguidor=request.user) | Q(seguido=request.user), pk=pk)
        conf.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VisitasDaPessoaView(generics.ListAPIView):
    """Visitas que uma pessoa que eu sigo liberou para pessoas de confiança. ?ocasiao= filtra; ?boas=1 só 4 e 5 sóis."""

    serializer_class = VisitaCompartilhadaSerializer

    def get_queryset(self):
        alvo = get_object_or_404(
            Usuario,
            pk=self.kwargs["pk"],
            confianca_recebida__seguidor=self.request.user,
            confianca_recebida__estado=Confianca.Estado.ACEITO,
        )
        self.alvo = alvo
        visitas = (
            visitas_compartilhadas(alvo)
            .select_related("lugar")
            .prefetch_related("tags", "lugar__tags", "lugar__motivos_comunidade__tag")
            .order_by("-visitado_em", "-id")
        )
        ocasiao = self.request.query_params.get("ocasiao", "")
        if ocasiao in Ocasiao.values:
            visitas = visitas.filter(ocasiao=ocasiao)
        if self.request.query_params.get("boas") == "1":
            visitas = visitas.filter(nota__gte=4)
        return visitas

    def list(self, request, *args, **kwargs):
        resposta = super().list(request, *args, **kwargs)
        resposta.data["pessoa"] = pessoa(self.alvo)
        return resposta
