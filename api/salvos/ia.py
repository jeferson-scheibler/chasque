"""Cliente da IA que lê o texto de um link salvo (ver docs/plano-intencao.md).

O resto do Chasque só conhece esta interface: `Entrada` vai, `Leitura` volta, `ErroIA` quando não deu.
Os testes trocam o cliente por um simulado; nenhum teste chama a rede.
"""

from dataclasses import dataclass, field
from typing import Protocol


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
    """A IA não respondeu, demorou demais ou respondeu fora do formato."""


class Cliente(Protocol):
    modelo: str

    def ler(self, entrada: Entrada) -> Leitura: ...


def cliente_padrao() -> Cliente | None:
    """O cliente configurado, ou None quando não há chave (aí nada é enviado e as intenções esperam).

    O cliente do Gemini (com settings.GEMINI_CHAVE e settings.GEMINI_MODELO) entra no passo 2 do plano.
    Até lá não há cliente real: só os testes leem intenções.
    """
    return None
