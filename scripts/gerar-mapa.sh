#!/usr/bin/env bash
# Gera o mapa do RS (dados/mapa/rs.pmtiles) a partir do arquivo do OpenStreetMap já baixado por importar-osm.sh.
# Usa osmium (recorte pelo contorno do RS) e tilemaker (esquema OpenMapTiles), ambos do Debian, na imagem
# de ferramentas (mapa/Dockerfile). Leva alguns minutos e uns 2 GB de disco temporário.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p dados/mapa
docker build -q -t chasque-ferramentas mapa >/dev/null
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD/dados:/dados" -v "$PWD/mapa:/mapa:ro" chasque-ferramentas sh -c '
  set -e
  cd /dados/mapa
  osmium getid -r /dados/osm/sul-latest.osm.pbf r242620 -o contorno.osm.pbf --overwrite
  osmium extract -p contorno.osm.pbf -s smart /dados/osm/sul-latest.osm.pbf -o rs.osm.pbf --overwrite
  rm -rf store && mkdir store
  tilemaker --input rs.osm.pbf --output rs.pmtiles --config /mapa/tilemaker-config.json \
    --process /usr/share/doc/tilemaker/examples/process-openmaptiles.lua --store store
  rm -rf store contorno.osm.pbf
  ls -la rs.pmtiles
'
