import json
import time

from django.core.management.base import BaseCommand, CommandError

from lugares.busca import sem_acento
from lugares.models import Tag
from salvos import ia


def normal(texto):
    return sem_acento(texto or "").casefold().strip()


class Command(BaseCommand):
    help = "Roda a IA sobre um arquivo de legendas com a resposta esperada e mede os acertos. Não grava nada."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", help='JSON com {"casos": [{"texto", "tipo", "perfil", "cidade_base", "esperado"}]}')
        parser.add_argument("--pausa", type=float, default=7, metavar="SEGUNDOS",
                            help="Espera entre chamadas, para caber no limite por minuto da camada gratuita.")

    def handle(self, arquivo, pausa, **_):
        cliente = ia.cliente_padrao()
        if cliente is None:
            raise CommandError("IA não configurada: defina GEMINI_CHAVE no .env.")
        try:
            with open(arquivo, encoding="utf-8") as f:
                casos = json.load(f)["casos"]
        except (OSError, ValueError, KeyError) as erro:
            raise CommandError(f"Não consegui ler {arquivo}: {erro}") from erro
        motivos = list(Tag.objects.values_list("slug", "nome"))

        certos_tag = dados_tag = esperados_tag = 0
        certos_util = certos_lugar = casos_lugar = lidos = 0
        for i, caso in enumerate(casos, 1):
            if i > 1:
                time.sleep(pausa)
            entrada = ia.Entrada(tipo=caso.get("tipo", "post"), perfil=caso.get("perfil", ""), texto=caso["texto"],
                                 cidade_base=caso.get("cidade_base", ""), motivos=motivos)
            try:
                leitura = cliente.ler(entrada)
            except ia.ErroIA as erro:
                self.stdout.write(f"{i:>3}  erro: {erro}")
                continue
            except ia.IAIndisponivel as erro:
                self.stdout.write(f"{i:>3}  IA indisponível, parei aqui: {str(erro)[:300]}")
                break
            lidos += 1
            esperado = caso.get("esperado", {})
            util = leitura.confianca != "baixa"
            tags = set(leitura.tags[:3]) if util else set()
            alvo = set(esperado.get("tags", []))
            certos_tag += len(tags & alvo)
            dados_tag += len(tags)
            esperados_tag += len(alvo)
            certos_util += util == esperado.get("util", True)
            if esperado.get("lugar_nome"):
                casos_lugar += 1
                certos_lugar += normal(esperado["lugar_nome"]) in normal(leitura.lugar_nome) and bool(leitura.lugar_nome)
            self.stdout.write(
                f"{i:>3}  {leitura.confianca:<5}  {leitura.frase[:60]:<60}  "
                f"tags {sorted(tags)} (esperado {sorted(alvo)})  lugar '{leitura.lugar_nome}'"
            )

        def pct(a, b):
            return f"{100 * a / b:.0f}%" if b else "-"

        self.stdout.write("")
        self.stdout.write(f"Modelo: {cliente.modelo}. Casos lidos: {lidos} de {len(casos)}.")
        self.stdout.write(f"Útil ou não (confiança): {pct(certos_util, lidos)} de acerto.")
        self.stdout.write(f"Motivos: precisão {pct(certos_tag, dados_tag)}, cobertura {pct(certos_tag, esperados_tag)}.")
        self.stdout.write(f"Nome do lugar: {pct(certos_lugar, casos_lugar)} de acerto.")
