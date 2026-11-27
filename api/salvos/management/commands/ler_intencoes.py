import time

from django.core.management.base import BaseCommand, CommandError

from contas.models import Usuario
from salvos import ia
from salvos.intencoes import marcar_todos, processar


class Command(BaseCommand):
    help = "Lê, com a IA, por que as pessoas salvaram os links que estão na fila."

    def add_arguments(self, parser):
        parser.add_argument("--repetir", type=int, default=0, metavar="MINUTOS",
                            help="Fica rodando, uma vez a cada MINUTOS (para o container do leitor).")
        parser.add_argument("--todos", metavar="EMAIL",
                            help="Antes de ler, põe na fila todos os salvos com texto dessa pessoa.")

    def handle(self, repetir, todos, **_):
        if todos:
            usuario = Usuario.objects.filter(email=todos.strip().lower()).first()
            if usuario is None:
                raise CommandError(f"Ninguém com o e-mail {todos}.")
            self.stdout.write(f"{marcar_todos(usuario)} salvos na fila.")

        avisou = False
        while True:
            if ia.cliente_padrao() is None:
                if not avisou:
                    self.stdout.write("IA não configurada: nada é enviado e as intenções ficam na fila.")
                    avisou = True
            else:
                self.stdout.write(f"{processar()} intenções lidas.")
            if not repetir:
                return
            time.sleep(repetir * 60)
