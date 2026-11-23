"""Entrega do refresh token.

Web: cookie httpOnly, que o JavaScript nao le.
Mobile (header X-Chasque-Cliente: mobile): no corpo da resposta, para o app guardar
no armazenamento seguro do aparelho.

Regra de seguranca: um token que chegou por cookie so volta por cookie. Assim um
script injetado na pagina nao consegue trocar o cookie por um token legivel.
"""

from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

HEADER_CLIENTE = "X-Chasque-Cliente"


def cliente_mobile(request):
    return request.headers.get(HEADER_CLIENTE, "").lower() == "mobile"


def gravar_cookie(response, refresh):
    cfg = settings.REFRESH_COOKIE
    response.set_cookie(
        cfg["name"],
        refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=cfg["secure"],
        samesite=cfg["samesite"],
        path=cfg["path"],
    )


def apagar_cookie(response):
    cfg = settings.REFRESH_COOKIE
    response.delete_cookie(cfg["name"], path=cfg["path"], samesite=cfg["samesite"])


def ler_refresh(request):
    """Retorna (token, veio_do_cookie)."""
    corpo = request.data if isinstance(request.data, dict) else {}
    token = corpo.get("refresh")
    if token:
        return token, False
    return request.COOKIES.get(settings.REFRESH_COOKIE["name"]), True


def entregar(response, request, refresh, por_cookie=None):
    """Coloca o refresh no lugar certo. por_cookie=None decide pelo tipo de cliente."""
    if por_cookie is None:
        por_cookie = not cliente_mobile(request)
    if por_cookie:
        gravar_cookie(response, refresh)
    else:
        response.data["refresh"] = refresh
    return response


def tokens_para(usuario):
    refresh = RefreshToken.for_user(usuario)
    return str(refresh.access_token), str(refresh)
