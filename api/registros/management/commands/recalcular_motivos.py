from django.core.management.base import BaseCommand

from registros.comunidade import recalcular_motivos
from registros.models import Registro


class Command(BaseCommand):
    help = "Recalcula os motivos da comunidade de todos os lugares com visitas (ex.: depois de mudar o mínimo de pessoas)."

    def handle(self, *args, **opcoes):
        lugares = Registro.objects.values_list("lugar_id", flat=True).distinct()
        recalcular_motivos(lugares)
        self.stdout.write(self.style.SUCCESS(f"{len(set(lugares))} lugares recalculados."))
