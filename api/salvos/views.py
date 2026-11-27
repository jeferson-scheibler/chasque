from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, Max, OuterRef, Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from lugares.models import Lugar
from lugares.serializers import LugarSerializer
from registros.models import Registro

from . import instagram
from .models import Salvo
from .serializers import CompartilhamentoSerializer, SalvoSerializer


def com_visita(salvos):
    """Marca os salvos cujo lugar a pessoa já visitou (registrou visita)."""
    return salvos.annotate(
        visitado=Exists(Registro.objects.filter(usuario=OuterRef("usuario"), lugar=OuterRef("lugar")))
    )


class SalvosView(generics.ListAPIView):
    """GET: lista o que a pessoa salvou (?pendentes=1 só os sem lugar).
    POST: recebe um compartilhamento e guarda o link do Instagram."""

    serializer_class = SalvoSerializer

    def get_queryset(self):
        salvos = com_visita(Salvo.objects.filter(usuario=self.request.user)).select_related("lugar").prefetch_related("lugar__tags", "lugar__motivos_comunidade__tag")
        if self.request.query_params.get("pendentes") == "1":
            salvos = salvos.filter(lugar__isnull=True)
        lugar = self.request.query_params.get("lugar", "")
        if lugar.isdigit():
            salvos = salvos.filter(lugar_id=int(lugar))
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
        lugar = dados.get("lugar_id")  # vindo da página do lugar: "adicionar outro post ou reel"

        existente = Salvo.objects.filter(usuario=request.user, url=link.url).first()
        if existente:
            mudou = []
            if texto and not existente.texto:
                existente.texto = texto
                mudou.append("texto")
            if lugar and existente.lugar_id != lugar.id:
                existente.lugar = lugar
                mudou.append("lugar")
            if mudou:
                existente.save(update_fields=[*mudou, "atualizado_em"])
            return self.resposta(existente, ja_salvo=True)

        try:
            with transaction.atomic():
                salvo = Salvo.objects.create(
                    usuario=request.user, url=link.url, tipo=link.tipo, perfil=link.perfil, texto=texto, lugar=lugar
                )
        except IntegrityError:  # dois compartilhamentos iguais ao mesmo tempo
            return self.resposta(Salvo.objects.get(usuario=request.user, url=link.url), ja_salvo=True)
        return self.resposta(salvo, ja_salvo=False)

    def resposta(self, salvo, ja_salvo):
        """`ja_salvo` diz ao app se o link já estava na lista (aí ele não pergunta de novo qual é o lugar)."""
        salvo = self.get_queryset().get(pk=salvo.pk)
        return Response({**SalvoSerializer(salvo).data, "ja_salvo": ja_salvo},
                        status=status.HTTP_200_OK if ja_salvo else status.HTTP_201_CREATED)


class MeusLugaresView(APIView):
    """Lugares que a pessoa já tem: ligados a algum link salvo ou com visita registrada.
    Os mais recentes primeiro; ?q= filtra pelo nome. Serve para a pergunta "de qual lugar é esse post?"."""

    LIMITE = 30

    def get(self, request):
        usuario = request.user
        lugares = (
            Lugar.objects.filter(Q(salvos__usuario=usuario) | Q(registros__usuario=usuario))
            .annotate(
                links=Count("salvos", filter=Q(salvos__usuario=usuario), distinct=True),
                visitas=Count("registros", filter=Q(registros__usuario=usuario), distinct=True),
                recente=Max("salvos__atualizado_em", filter=Q(salvos__usuario=usuario)),
                visita=Max("registros__criado_em", filter=Q(registros__usuario=usuario)),
            )
            .prefetch_related("tags", "motivos_comunidade__tag")
        )
        termo = request.query_params.get("q", "").strip()[:80]
        if termo:
            lugares = lugares.filter(nome__unaccent__icontains=termo)
        lugares = sorted(lugares, key=lambda l: max(d for d in (l.recente, l.visita) if d), reverse=True)
        return Response([
            {**LugarSerializer(l).data, "links": l.links, "visitado": l.visitas > 0}
            for l in lugares[: self.LIMITE]
        ])


class SalvoView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SalvoSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return com_visita(Salvo.objects.filter(usuario=self.request.user)).select_related("lugar").prefetch_related("lugar__tags", "lugar__motivos_comunidade__tag")
