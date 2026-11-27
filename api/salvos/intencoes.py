"""Intenção do link salvo: por que a pessoa quis ir (ver docs/plano-intencao.md).

1. `marcar_pendente` roda quando um salvo nasce ou o texto muda. Não chama a IA, só deixa na fila.
2. `processar` (comando ler_intencoes) lê as pendentes em lote, fora do request.
3. `aplicar` valida o que a IA devolveu: só motivos que existem, no máximo 3, e lugar só pela nossa busca.
"""

import hashlib
import logging

from django.db import transaction
from django.utils import timezone

from lugares.busca import por_nome, sem_acento
from lugares.models import Lugar, Tag

from . import ia
from .models import Intencao, Salvo

log = logging.getLogger(__name__)

VERSAO_PROMPT = "1"
MAX_TAGS = 3
MAX_TENTATIVAS = 3
# Por minuto (o leitor roda a cada minuto). A camada gratuita do Gemini aceita poucas chamadas por minuto.
LOTE = 5
# Chamadas por pessoa por dia. O que passar disso fica pendente para o dia seguinte.
LIMITE_DIA = 30


def hash_da_entrada(salvo):
    base = "\n".join([VERSAO_PROMPT, salvo.tipo, salvo.perfil, salvo.texto.strip()])
    return hashlib.sha256(base.encode()).hexdigest()


def marcar_pendente(salvo):
    """Põe o salvo na fila de leitura se a pessoa ligou a IA e há texto novo. Devolve a intenção ou None."""
    if not salvo.usuario.usar_ia or not salvo.texto.strip():
        return None
    entrada = hash_da_entrada(salvo)
    intencao, criada = Intencao.objects.get_or_create(salvo=salvo, defaults={"hash_entrada": entrada})
    if criada:
        return intencao
    # o que a pessoa confirmou ou editou não é sobrescrito, e texto igual não é lido de novo
    if intencao.estado == Intencao.Estado.CONFIRMADA or intencao.hash_entrada == entrada:
        return intencao
    intencao.estado = Intencao.Estado.PENDENTE
    intencao.hash_entrada = entrada
    intencao.tentativas = 0
    intencao.save(update_fields=["estado", "hash_entrada", "tentativas", "atualizado_em"])
    return intencao


def marcar_todos(usuario):
    """Põe na fila todos os salvos com texto da pessoa (para quem acabou de ligar a IA). Devolve quantos."""
    return sum(1 for salvo in Salvo.objects.filter(usuario=usuario).exclude(texto="") if marcar_pendente(salvo))


def lidas_hoje(usuario):
    return Intencao.objects.filter(salvo__usuario=usuario, lida_em__date=timezone.localdate()).count()


def processar(cliente=None, limite=LOTE):
    """Lê um lote de intenções pendentes. Devolve quantas foram lidas (com ou sem sucesso)."""
    cliente = cliente or ia.cliente_padrao()
    if cliente is None:
        return 0
    pendentes = (
        Intencao.objects.filter(estado=Intencao.Estado.PENDENTE, salvo__usuario__usar_ia=True)
        .select_related("salvo__usuario")
        .order_by("atualizado_em")
    )
    motivos = list(Tag.objects.values_list("slug", "nome"))
    lidas = 0
    no_limite = set()  # quem já leu LIMITE_DIA hoje fica para amanhã, sem travar a fila dos outros
    for intencao in pendentes.iterator():
        usuario = intencao.salvo.usuario
        if usuario.pk in no_limite or lidas_hoje(usuario) >= LIMITE_DIA:
            no_limite.add(usuario.pk)
            continue
        try:
            ler(intencao, cliente, motivos)
        except ia.IAIndisponivel as erro:
            # vale para todos: o resto da fila espera a próxima rodada, sem gastar tentativas
            log.warning("IA indisponível, lote interrompido: %s", erro)
            break
        lidas += 1
        if lidas >= limite:
            break
    return lidas


def ler(intencao, cliente, motivos):
    salvo = intencao.salvo
    entrada = ia.Entrada(
        tipo=salvo.tipo, perfil=salvo.perfil, texto=salvo.texto.strip(),
        cidade_base=salvo.usuario.cidade_base, motivos=motivos,
    )
    intencao.lida_em = timezone.now()
    try:
        leitura = cliente.ler(entrada)
    except ia.ErroIA as erro:
        intencao.tentativas += 1
        if intencao.tentativas >= MAX_TENTATIVAS:
            intencao.estado = Intencao.Estado.FALHOU
        log.warning("intenção %s não lida (%s tentativas): %s", intencao.pk, intencao.tentativas, erro)
        intencao.save(update_fields=["tentativas", "estado", "lida_em", "atualizado_em"])
        return
    aplicar(intencao, leitura, modelo=getattr(cliente, "modelo", ""))


@transaction.atomic
def aplicar(intencao, leitura, modelo=""):
    """Grava a leitura, validada. Confiança baixa não deixa frase nem motivos: só o nome do lugar, se houver."""
    confianca = leitura.confianca if leitura.confianca in Intencao.Confianca.values else Intencao.Confianca.BAIXA
    util = confianca != Intencao.Confianca.BAIXA

    slugs = []
    for slug in leitura.tags if util else []:
        if isinstance(slug, str) and slug not in slugs:
            slugs.append(slug)
    tags = {t.slug: t for t in Tag.objects.filter(slug__in=slugs)}
    escolhidas = [tags[s] for s in slugs if s in tags][:MAX_TAGS]

    intencao.frase = " ".join(leitura.frase.split())[:120] if util else ""
    intencao.confianca = confianca
    intencao.lugar_nome = " ".join(leitura.lugar_nome.split())[:200]
    intencao.lugar_cidade = " ".join(leitura.lugar_cidade.split())[:120]
    intencao.lugar_sugerido = (
        None if intencao.salvo.lugar_id else encontrar_lugar(intencao.lugar_nome, intencao.lugar_cidade)
    )
    intencao.modelo = modelo[:60]
    intencao.versao_prompt = VERSAO_PROMPT
    intencao.estado = Intencao.Estado.PRONTA
    intencao.save()
    intencao.tags.set(escolhidas)


def encontrar_lugar(nome, cidade):
    """O lugar da base com esse nome (e cidade, se veio), só quando não há dúvida. Senão, None."""
    q = sem_acento(nome.strip())[:100]
    if len(q) < 3:
        return None
    candidatos = por_nome(Lugar.objects.all(), q)
    if cidade.strip():
        candidatos = candidatos.filter(cidade__unaccent__iexact=sem_acento(cidade.strip()))
    candidatos = list(candidatos.order_by("-semelhanca", "nome")[:5])
    if len(candidatos) == 1:
        return candidatos[0]
    exatos = [l for l in candidatos if sem_acento(l.nome).casefold() == q.casefold()]
    return exatos[0] if len(exatos) == 1 else None


def frases_por_lugar(usuario_id, lugar_ids):
    """A frase do motivo de cada lugar, tirada do link mais recente que tiver uma (lida pela IA ou confirmada).

    Serve para o roteiro e o aviso de fim de semana lembrarem por que a pessoa quis ir.
    """
    frases = {}
    intencoes = (
        Intencao.objects.filter(
            salvo__usuario_id=usuario_id,
            salvo__lugar_id__in=lugar_ids,
            estado__in=[Intencao.Estado.PRONTA, Intencao.Estado.CONFIRMADA],
        )
        .exclude(frase="")
        .order_by("-salvo__criado_em")
        .values_list("salvo__lugar_id", "frase")
    )
    for lugar_id, frase in intencoes:
        frases.setdefault(lugar_id, frase)
    return frases
