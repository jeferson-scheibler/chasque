import time

from django.core.management.base import BaseCommand

from agenda.planejar import planejar


class Command(BaseCommand):
    help = "Lê as agendas, monta roteiros para os fins de semana livres e manda os avisos."

    def add_arguments(self, parser):
        parser.add_argument("--forcar", action="store_true", help="Lê todas as agendas agora.")
        parser.add_argument("--repetir", type=int, default=0, metavar="MINUTOS",
                            help="Fica rodando, uma vez a cada MINUTOS (para o container do agendador).")

    def handle(self, forcar, repetir, **_):
        while True:
            lidas, avisados = planejar(forcar=forcar)
            self.stdout.write(f"{lidas} agendas lidas, {avisados} avisos enviados.")
            if not repetir:
                return
            forcar = False
            time.sleep(repetir * 60)
