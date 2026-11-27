"""Cliente da IA que lê o texto de um link salvo (ver docs/plano-intencao.md).

O resto do Chasque só conhece esta interface: `Entrada` vai, `Leitura` volta, `ErroIA` quando não deu para
ler aquele texto e `IAIndisponivel` quando a IA não está atendendo.
Os testes trocam o cliente por um simulado; nenhum teste chama a rede.
"""

from dataclasses import dataclass, field
from typing import Protocol

from django.conf import settings


@dataclass(frozen=True)
class Entrada:
    tipo: str  # post, reel ou perfil
    perfil: str  # @ do Instagram, quando vem no link
    texto: str  # legenda colada ou anotação da pessoa
    cidade_base: str
    motivos: list[tuple[str, str]]  # (slug, nome) das tags que a resposta pode usar


@dataclass(frozen=True)
class Leitura:
    """O que a IA devolveu, ainda sem validar (quem valida é intencoes.aplicar)."""

    frase: str = ""
    tags: list[str] = field(default_factory=list)
    lugar_nome: str = ""
    lugar_cidade: str = ""
    confianca: str = "baixa"


class ErroIA(Exception):
    """Não deu para ler este texto (resposta bloqueada ou fora do formato). Conta como tentativa."""


class IAIndisponivel(Exception):
    """A IA não está atendendo agora (limite da conta, chave, rede, fora do ar). Para o lote sem gastar tentativas."""


class Cliente(Protocol):
    modelo: str

    def ler(self, entrada: Entrada) -> Leitura: ...


def cliente_padrao() -> Cliente | None:
    """O cliente configurado, ou None quando não há chave (aí nada é enviado e as intenções esperam)."""
    if not settings.GEMINI_CHAVE:
        return None
    from .gemini import ClienteGemini

    return ClienteGemini(chave=settings.GEMINI_CHAVE, modelo=settings.GEMINI_MODELO)
