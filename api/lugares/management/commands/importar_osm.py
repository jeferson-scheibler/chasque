from django.core.management.base import BaseCommand, CommandError

from lugares import osm


class Command(BaseCommand):
    help = "Importa lugares do OpenStreetMap a partir de um .osm.pbf (ex.: Geofabrik, região Sul)."

    def add_arguments(self, parser):
        origem = parser.add_mutually_exclusive_group(required=True)
        origem.add_argument("--pbf", help="Arquivo .osm.pbf. Será recortado pela caixa --bbox.")
        origem.add_argument("--geojson", help="Saída pronta do `osmium export -f geojsonseq` (pula o osmium).")
        parser.add_argument(
            "--relacao",
            type=int,
            help=f"Recorta pelo contorno desta relação do OSM em vez da caixa. RS = {osm.RELACAO_RS}.",
        )
        parser.add_argument(
            "--bbox",
            default=",".join(str(v) for v in osm.BBOX_VALE),
            help="oeste,sul,leste,norte. Padrão: Vale do Taquari e arredores.",
        )

    def handle(self, *args, **opcoes):
        caminho = opcoes["geojson"]
        if opcoes["pbf"]:
            try:
                bbox = tuple(float(v) for v in opcoes["bbox"].split(","))
                assert len(bbox) == 4
            except (ValueError, AssertionError):
                raise CommandError("--bbox precisa de 4 números: oeste,sul,leste,norte")
            self.stdout.write("Recortando e filtrando com osmium...")
            try:
                caminho = osm.extrair_pbf(opcoes["pbf"], bbox, relacao=opcoes["relacao"])
            except FileNotFoundError:
                raise CommandError("osmium não encontrado. Ele vem na imagem Docker da API.")
            except Exception as erro:
                raise CommandError(f"osmium falhou: {getattr(erro, 'stderr', erro)}")

        self.stdout.write("Gravando os lugares...")
        resumo = osm.importar(osm.ler_geojsonseq(caminho), progresso=lambda n: self.stdout.write(f"  {n} lidos"))
        self.stdout.write(self.style.SUCCESS(
            f"{resumo['lugares_novos']} lugares novos, "
            f"{resumo['lugares_atualizados']} atualizados, {resumo['ignorados']} ignorados."
        ))
