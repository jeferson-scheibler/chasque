from django.db import IntegrityError, transaction
from rest_framework import generics, status
from rest_framework.response import Response

from . import instagram
from .models import Salvo
from .serializers import CompartilhamentoSerializer, SalvoSerializer


class SalvosView(generics.ListAPIView):
    """GET: lista o que a pessoa salvou (?pendentes=1 só os sem lugar).
    POST: recebe um compartilhamento e guarda o link do Instagram."""

    serializer_class = SalvoSerializer

    def get_queryset(self):
        salvos = Salvo.objects.filter(usuario=self.request.user).select_related("lugar").prefetch_related("lugar__tags")
        if self.request.query_params.get("pendentes") == "1":
            salvos = salvos.filter(lugar__isnull=True)
        return salvos

    def post(self, request):
        entrada = CompartilhamentoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data

        link = instagram.encontrar(dados.get("url"), dados.get("text"), dados.get("title"))
        if link is None:
            return Response(
                {"url": ["Não encontrei um link de post, reel ou perfil do Instagram."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        texto = instagram.limpar_texto(dados.get("text", ""))[:2000]

        existente = Salvo.objects.filter(usuario=request.user, url=link.url).first()
        if existente:
            if texto and not existente.texto:
                existente.texto = texto
                existente.save(update_fields=["texto", "atualizado_em"])
            return Response(SalvoSerializer(existente).data, status=status.HTTP_200_OK)

        try:
            with transaction.atomic():
                salvo = Salvo.objects.create(
                    usuario=request.user, url=link.url, tipo=link.tipo, perfil=link.perfil, texto=texto
                )
        except IntegrityError:  # dois compartilhamentos iguais ao mesmo tempo
            salvo = Salvo.objects.get(usuario=request.user, url=link.url)
            return Response(SalvoSerializer(salvo).data, status=status.HTTP_200_OK)
        return Response(SalvoSerializer(salvo).data, status=status.HTTP_201_CREATED)


class SalvoView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SalvoSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Salvo.objects.filter(usuario=self.request.user).select_related("lugar")
