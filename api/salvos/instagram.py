"""Leitura de links do Instagram compartilhados com o Chasque.

O Chasque só guarda o link. Não baixa a página do Instagram (os termos de uso
proíbem coleta automatizada); quem diz qual é o lugar é a própria pessoa.

Os parâmetros de rastreio (igsh, utm_*, etc.) são descartados: o link guardado
fica só com o caminho do post, reel ou perfil.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

RE_LINK = re.compile(r"https?://(?:www\.|m\.)?(?:instagram\.com|instagr\.am)/[^\s<>\"'()]+", re.IGNORECASE)
RE_CODIGO = re.compile(r"^[A-Za-z0-9_-]{5,64}$")
RE_PERFIL = re.compile(r"^[A-Za-z0-9._]{1,30}$")

TIPOS_POST = {"p": "post", "reel": "reel", "reels": "reel", "tv": "reel"}
RESERVADOS = {
    "explore", "accounts", "about", "developer", "legal", "direct", "web", "api", "challenge",
    "privacy", "terms", "share", "emails", "session", "oauth", "graphql", "static", "directory",
}


@dataclass(frozen=True)
class LinkInstagram:
    url: str
    tipo: str  # post, reel ou perfil
    perfil: str = ""


def _perfil_valido(nome):
    return bool(RE_PERFIL.match(nome)) and nome.lower() not in RESERVADOS and not nome.startswith(".")


def normalizar(url):
    """Converte um link do Instagram para a forma canônica, sem rastreio. None se não for post, reel ou perfil."""
    partes = urlsplit(url.strip())
    if partes.hostname is None or not re.fullmatch(r"(www\.|m\.)?(instagram\.com|instagr\.am)", partes.hostname, re.I):
        return None
    caminho = [p for p in partes.path.split("/") if p]
    if not caminho:
        return None

    # /share/reel/CODIGO e /share/p/CODIGO: link curto do app. Guardamos como veio, sem a query.
    if caminho[0].lower() == "share":
        if len(caminho) >= 3 and caminho[1].lower() in TIPOS_POST and RE_CODIGO.match(caminho[2]):
            tipo = TIPOS_POST[caminho[1].lower()]
            return LinkInstagram(f"https://www.instagram.com/share/{caminho[1].lower()}/{caminho[2]}/", tipo)
        if len(caminho) == 2 and RE_CODIGO.match(caminho[1]):
            return LinkInstagram(f"https://www.instagram.com/share/{caminho[1]}/", "post")
        return None

    # /p/CODIGO, /reel/CODIGO, /tv/CODIGO
    if caminho[0].lower() in TIPOS_POST and len(caminho) >= 2 and RE_CODIGO.match(caminho[1]):
        tipo = TIPOS_POST[caminho[0].lower()]
        return LinkInstagram(f"https://www.instagram.com/{'reel' if tipo == 'reel' else 'p'}/{caminho[1]}/", tipo)

    # /perfil/p/CODIGO e /perfil/reel/CODIGO (formato novo, com o autor no caminho)
    if len(caminho) >= 3 and caminho[1].lower() in TIPOS_POST and RE_CODIGO.match(caminho[2]) and _perfil_valido(caminho[0]):
        tipo = TIPOS_POST[caminho[1].lower()]
        return LinkInstagram(
            f"https://www.instagram.com/{'reel' if tipo == 'reel' else 'p'}/{caminho[2]}/", tipo, caminho[0].lower()
        )

    # /stories/perfil/123: stories somem em 24 h; guardamos o perfil.
    if caminho[0].lower() == "stories" and len(caminho) >= 2 and _perfil_valido(caminho[1]):
        perfil = caminho[1].lower()
        return LinkInstagram(f"https://www.instagram.com/{perfil}/", "perfil", perfil)

    # /perfil
    if len(caminho) == 1 and _perfil_valido(caminho[0]):
        perfil = caminho[0].lower()
        return LinkInstagram(f"https://www.instagram.com/{perfil}/", "perfil", perfil)

    return None


def encontrar(*textos):
    """Primeiro link válido do Instagram dentro dos textos recebidos (url, text, title do compartilhamento)."""
    for texto in textos:
        for trecho in RE_LINK.findall(texto or ""):
            link = normalizar(trecho.rstrip(".,;!?"))
            if link:
                return link
    return None


def limpar_texto(texto):
    """Texto compartilhado sem os links (o Instagram costuma mandar só o link no campo de texto)."""
    return re.sub(r"\s+\n", "\n", RE_LINK.sub("", texto or "")).strip()
