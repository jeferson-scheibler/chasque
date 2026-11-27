"""Avisos no celular por Web Push (chaves VAPID no .env)."""

import json
import logging
from urllib.parse import urlsplit

from django.conf import settings
from pywebpush import WebPushException, webpush

log = logging.getLogger(__name__)

# O servidor faz um POST no endpoint que o navegador deu: só aceitamos os serviços de push conhecidos.
SERVICOS = ("fcm.googleapis.com", "push.services.mozilla.com", "push.apple.com", "notify.windows.com")


def configurado():
    return bool(settings.VAPID_PUBLICA and settings.VAPID_PRIVADA)


def endpoint_valido(url):
    partes = urlsplit(url or "")
    host = (partes.hostname or "").lower()
    return partes.scheme == "https" and partes.port in (None, 443) and any(
        host == s or host.endswith("." + s) for s in SERVICOS
    )


def enviar(usuario, titulo, corpo, url, tag="chasque"):
    """Manda para todos os aparelhos da pessoa. Devolve quantos receberam."""
    if not configurado():
        return 0
    carga = json.dumps({"titulo": titulo, "corpo": corpo, "url": url, "tag": tag})
    enviados = 0
    for inscricao in list(usuario.inscricoes_push.all()):
        if not endpoint_valido(inscricao.endpoint):
            inscricao.delete()
            continue
        try:
            webpush(
                subscription_info={"endpoint": inscricao.endpoint,
                                   "keys": {"p256dh": inscricao.p256dh, "auth": inscricao.auth}},
                data=carga,
                vapid_private_key=settings.VAPID_PRIVADA,
                vapid_claims={"sub": settings.VAPID_CONTATO},
                ttl=12 * 3600,
                timeout=10,
            )
            enviados += 1
        except WebPushException as erro:
            codigo = getattr(erro.response, "status_code", None)
            if codigo in (404, 410):  # o aparelho cancelou a inscrição
                inscricao.delete()
            else:
                log.warning("push falhou (%s) para a inscrição %s", codigo, inscricao.pk)
        except Exception:  # rede fora do ar, chave inválida: não derruba o planejamento
            log.exception("push falhou para a inscrição %s", inscricao.pk)
    return enviados
