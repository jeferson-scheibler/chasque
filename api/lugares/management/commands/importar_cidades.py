from django.core.management.base import BaseCommand, CommandError

from lugares import osm


class Command(BaseCommand):
    help = "Importa todos os municípios de uma UF (padrão: RS) do OpenStreetMap, com a posição da sede."

    def add_arguments(self, parser):
        parser.add_argument("--pbf", required=True, help="Arquivo .osm.pbf que cubra a UF (ex.: Geofabrik, região Sul).")
        parser.add_argument("--ibge", default="43", help="Prefixo do código IBGE da UF. 43 = Rio Grande do Sul.")

    def handle(self, *args, **opcoes):
        self.stdout.write("Lendo os municípios com osmium...")
        try:
            municipios = osm.extrair_municipios(opcoes["pbf"], opcoes["ibge"])
        except FileNotFoundError:
            raise CommandError("osmium não encontrado. Ele vem na imagem Docker da API.")
        except Exception as erro:
            raise CommandError(f"osmium falhou: {getattr(erro, 'stderr', erro)}")
        if not municipios:
            raise CommandError("Nenhum município encontrado. Confira o arquivo e o prefixo IBGE.")
        resumo = osm.importar_municipios(municipios)
        self.stdout.write(self.style.SUCCESS(f"{resumo['cidades']} cidades ({resumo['novas']} novas)."))
