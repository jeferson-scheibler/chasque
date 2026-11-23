#!/usr/bin/env bash
# Baixa o recorte do Sul do Brasil da Geofabrik (uma vez por dia no máximo) e importa
# os municípios e os lugares do Rio Grande do Sul para o banco. Pode rodar de novo: atualiza sem duplicar.
set -euo pipefail

cd "$(dirname "$0")/.."
PASTA=dados/osm
ARQUIVO="$PASTA/sul-latest.osm.pbf"
URL=https://download.geofabrik.de/south-america/brazil/sul-latest.osm.pbf

mkdir -p "$PASTA"
if [[ ! -f "$ARQUIVO" || -n "$(find "$ARQUIVO" -mtime +0 2>/dev/null)" ]]; then
  echo "Baixando $URL (cerca de 430 MB)..."
  curl -fL --retry 3 -o "$ARQUIVO.parcial" "$URL"
  mv "$ARQUIVO.parcial" "$ARQUIVO"
fi

# Primeiro as cidades (todos os municípios do RS), depois os lugares, que usam a cidade mais próxima.
docker-compose run --rm api python manage.py importar_cidades --pbf "/$ARQUIVO"
# --relacao 242620: recorta pelo contorno do RS no OSM (sem pegar SC nem o Uruguai).
docker-compose run --rm api python manage.py importar_osm --pbf "/$ARQUIVO" --relacao 242620 "$@"
