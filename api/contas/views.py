from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from . import tokens
from .serializers import CadastroSerializer, EntrarSerializer, UsuarioSerializer


def _resposta_logada(request, usuario, codigo=status.HTTP_200_OK):
    access, refresh = tokens.tokens_para(usuario)
    resposta = Response({"access": access, "usuario": UsuarioSerializer(usuario).data}, status=codigo)
    return tokens.entregar(resposta, request, refresh)




def _intencao_exportada(salvo):
    """A intenção do salvo (lida pela IA ou escrita pela pessoa), para a exportação de dados."""
    from salvos.models import Intencao

    try:
        intencao = salvo.intencao
    except Intencao.DoesNotExist:
        return None
    return {
        "estado": intencao.estado,
        "frase": intencao.frase,
        "tags": [t.slug for t in intencao.tags.all()],
        "lugar_indicado": intencao.lugar_nome,
        "cidade_indicada": intencao.lugar_cidade,
        "modelo": intencao.modelo,
        "lida_em": intencao.lida_em,
    }
class CadastroView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "cadastro"

    def post(self, request):
        serializer = CadastroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        return _resposta_logada(request, usuario, status.HTTP_201_CREATED)


class EntrarView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = EntrarSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        usuario = serializer.validated_data["usuario"]
        if usuario is None:
            return Response({"detail": "E-mail ou senha incorretos."}, status=status.HTTP_401_UNAUTHORIZED)
        usuario.last_login = timezone.now()
        usuario.save(update_fields=["last_login"])
        return _resposta_logada(request, usuario)


class RenovarView(APIView):
    """Troca um refresh valido por um access novo. O refresh e rotacionado a cada uso.

    Limite próprio, mais folgado que o do login: o app renova a sessão sempre que abre, e várias
    pessoas na mesma rede (Wi-Fi da universidade) dividem o mesmo IP."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "renovar"

    def post(self, request):
        token, veio_do_cookie = tokens.ler_refresh(request)
        if not token:
            return Response({"detail": "Sessão expirada."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = TokenRefreshSerializer(data={"refresh": token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            resposta = Response({"detail": "Sessão expirada."}, status=status.HTTP_401_UNAUTHORIZED)
            if veio_do_cookie:
                tokens.apagar_cookie(resposta)
            return resposta

        dados = serializer.validated_data
        resposta = Response({"access": dados["access"]})
        return tokens.entregar(resposta, request, dados["refresh"], por_cookie=veio_do_cookie)


class SairView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token, _ = tokens.ler_refresh(request)
        if token:
            try:
                RefreshToken(token).blacklist()
            except TokenError:
                pass
        resposta = Response(status=status.HTTP_204_NO_CONTENT)
        tokens.apagar_cookie(resposta)
        return resposta


class MeView(generics.RetrieveUpdateAPIView):
    """Dados da propria conta. DELETE exclui a conta e todos os registros (LGPD)."""

    serializer_class = UsuarioSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        antes = serializer.instance.contribuir_motivos
        ia_antes = serializer.instance.usar_ia
        usuario = serializer.save()
        if usuario.usar_ia and not ia_antes:
            # quem liga a leitura quer ver os links que já tem lidos também (até o limite do dia)
            from salvos.intencoes import marcar_todos

            marcar_todos(usuario)
        if usuario.contribuir_motivos != antes:
            # entra ou sai da soma anônima dos lugares que visitou
            from registros.comunidade import lugares_de, recalcular_motivos

            recalcular_motivos(lugares_de(usuario))

    def delete(self, request):
        corpo = request.data if isinstance(request.data, dict) else {}
        if not request.user.check_password(corpo.get("senha", "")):
            return Response({"senha": ["Senha incorreta."]}, status=status.HTTP_400_BAD_REQUEST)

        from registros.comunidade import lugares_de, recalcular_motivos

        lugares = lugares_de(request.user)
        with transaction.atomic():
            for pendente in OutstandingToken.objects.filter(user=request.user):
                BlacklistedToken.objects.get_or_create(token=pendente)
            request.user.delete()
        recalcular_motivos(lugares)  # as visitas apagadas saem da soma dos lugares

        resposta = Response(status=status.HTTP_204_NO_CONTENT)
        tokens.apagar_cookie(resposta)
        return resposta


class ExportarView(APIView):
    """Portabilidade (LGPD art. 18): tudo que o Chasque guarda sobre a pessoa, em JSON."""

    def get(self, request):
        from agenda.models import Agenda, Roteiro
        from registros.models import PesoGosto, PreferenciaDeclarada, Registro
        from salvos.models import Salvo

        usuario = request.user
        registros = (
            Registro.objects.filter(usuario=usuario)
            .select_related("lugar", "intencao")
            .prefetch_related("tags")
            .order_by("-visitado_em")
        )
        dados = {
            "exportado_em": timezone.now().isoformat(),
            "usuario": {
                **UsuarioSerializer(usuario).data,
                "termos_aceitos_em": usuario.termos_aceitos_em,
                "versao_termos": usuario.versao_termos,
            },
            "registros": [
                {
                    "lugar": {
                        "nome": r.lugar.nome,
                        "endereco": r.lugar.endereco,
                        "lat": r.lugar.ponto.y,
                        "lng": r.lugar.ponto.x,
                    },
                    "visitado_em": r.visitado_em,
                    "ocasiao": r.ocasiao,
                    "nota": r.nota,
                    "motivo": r.motivo,
                    "tags": [t.slug for t in r.tags.all()],
                    "privado": r.privado,
                    "motivo_de_ter_salvo": r.intencao.frase if r.intencao else "",
                    "valeu": r.get_expectativa_display() if r.expectativa else "",
                }
                for r in registros
            ],
            "salvos": [
                {
                    "url": s.url,
                    "tipo": s.tipo,
                    "texto": s.texto,
                    "lugar": s.lugar.nome if s.lugar else None,
                    "criado_em": s.criado_em,
                    "intencao": _intencao_exportada(s),
                }
                for s in Salvo.objects.filter(usuario=usuario).select_related("lugar", "intencao")
                .prefetch_related("intencao__tags")
            ],
            # o endereço secreto da agenda é da própria pessoa: vai junto, para ela poder levar para outro lugar
            "agenda": next(
                ({"url": a.url, "lida_em": a.lida_em, "dias_livres": a.dias_livres}
                 for a in Agenda.objects.filter(usuario=usuario)),
                None,
            ),
            "roteiros": [
                {"dia": r.dia, "cidade": r.cidade, "paradas": [p.lugar.nome for p in r.paradas.all()]}
                for r in Roteiro.objects.filter(usuario=usuario).prefetch_related("paradas__lugar")
            ],
            "preferencias": sorted(
                PreferenciaDeclarada.objects.filter(usuario=usuario).values_list("tag__slug", flat=True)
            ),
            "pessoas_de_confianca": {
                "sigo": [c.seguido.nome for c in usuario.confianca_dada.select_related("seguido") if c.estado == "aceito"],
                "me_seguem": [
                    c.seguidor.nome for c in usuario.confianca_recebida.select_related("seguidor") if c.estado == "aceito"
                ],
            },
            "perfil_de_gosto": [
                {"tag": p.tag.slug, "ocasiao": p.ocasiao, "peso": p.peso}
                for p in PesoGosto.objects.filter(usuario=usuario).select_related("tag")
            ],
        }
        resposta = Response(dados)
        resposta["Content-Disposition"] = 'attachment; filename="chasque-meus-dados.json"'
        return resposta
