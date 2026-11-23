/**
 * Estilo do mapa do Chasque para MapLibre, sobre o esquema OpenMapTiles gerado pelo tilemaker
 * (scripts/gerar-mapa.sh). Duas paletas: dia (vale claro) e noite (vale escuro), nas cores da marca.
 * Mapa calmo de propósito: os lugares da pessoa são o que precisa aparecer.
 */
import type { ExpressionSpecification, StyleSpecification } from 'maplibre-gl'

interface Paleta {
  terra: string
  mata: string
  campo: string
  cidade: string
  parque: string
  agua: string
  predio: string
  via: string
  viaBorda: string
  viaPrincipal: string
  viaPrincipalBorda: string
  divisa: string
  texto: string
  textoSuave: string
  halo: string
}

const DIA: Paleta = {
  terra: '#f3eee3',
  mata: '#dfe3cc',
  campo: '#ece9d9',
  cidade: '#ece5d6',
  parque: '#d7e2c4',
  agua: '#c5d3e0',
  predio: '#e3dccd',
  via: '#ffffff',
  viaBorda: '#dcd2bf',
  viaPrincipal: '#f6dfae',
  viaPrincipalBorda: '#d9b977',
  divisa: '#1f2b4d',
  texto: '#1f2b4d',
  textoSuave: '#5d6374',
  halo: '#faf6ee',
}

const NOITE: Paleta = {
  terra: '#121a2d',
  mata: '#15213a',
  campo: '#141d33',
  cidade: '#18213a',
  parque: '#172641',
  agua: '#0a1020',
  predio: '#1d2741',
  via: '#27314f',
  viaBorda: '#121a2d',
  viaPrincipal: '#5a4a2c',
  viaPrincipalBorda: '#121a2d',
  divisa: '#a9b7e0',
  texto: '#f1ece2',
  textoSuave: '#9ba1b4',
  halo: '#0f1524',
}

const FONTE = ['Noto Sans Regular']
const FONTE_FORTE = ['Noto Sans Medium']
const NOME: ExpressionSpecification = ['coalesce', ['get', 'name:pt'], ['get', 'name'], ['get', 'name:latin']]

/** Largura de via que cresce com o zoom (exponencial, como o olho espera). */
function largura(z10: number, z18: number): ExpressionSpecification {
  return ['interpolate', ['exponential', 1.6], ['zoom'], 10, z10, 18, z18]
}

export function estiloDoMapa(escuro: boolean, urlDoArquivo: string): StyleSpecification {
  const c = escuro ? NOITE : DIA
  const principais = ['motorway', 'trunk', 'primary']
  const secundarias = ['secondary', 'tertiary']
  const menores = ['minor', 'service', 'unclassified', 'residential', 'living_street']

  return {
    version: 8,
    glyphs: '/mapa/fontes/{fontstack}/{range}.pbf',
    sources: {
      rs: {
        // Endereço dos pedaços em vez do cabeçalho do arquivo: o tilemaker 3.0 grava os limites como 0,0,0,0,
        // e com isso o MapLibre não pediria nada. Os limites do RS vão aqui.
        type: 'vector',
        tiles: [`pmtiles://${urlDoArquivo}/{z}/{x}/{y}`],
        minzoom: 0,
        maxzoom: 14,
        bounds: [-57.7, -33.8, -49.6, -27.0],
        attribution: '<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap</a>',
      },
    },
    layers: [
      { id: 'terra', type: 'background', paint: { 'background-color': c.terra } },
      {
        id: 'mata', type: 'fill', source: 'rs', 'source-layer': 'landcover',
        filter: ['in', ['get', 'class'], ['literal', ['wood', 'forest']]],
        paint: { 'fill-color': c.mata },
      },
      {
        id: 'campo', type: 'fill', source: 'rs', 'source-layer': 'landcover',
        filter: ['in', ['get', 'class'], ['literal', ['grass', 'farmland', 'meadow', 'scrub']]],
        paint: { 'fill-color': c.campo },
      },
      {
        id: 'cidade', type: 'fill', source: 'rs', 'source-layer': 'landuse',
        filter: ['in', ['get', 'class'], ['literal', ['residential', 'suburb', 'neighbourhood', 'commercial', 'retail']]],
        paint: { 'fill-color': c.cidade, 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 6, 0.6, 12, 1] },
      },
      { id: 'parque', type: 'fill', source: 'rs', 'source-layer': 'park', paint: { 'fill-color': c.parque } },
      { id: 'agua', type: 'fill', source: 'rs', 'source-layer': 'water', paint: { 'fill-color': c.agua } },
      {
        id: 'rio', type: 'line', source: 'rs', 'source-layer': 'waterway',
        paint: {
          'line-color': c.agua,
          'line-width': ['interpolate', ['linear'], ['zoom'], 8, ['match', ['get', 'class'], 'river', 1.2, 0.4], 14, ['match', ['get', 'class'], 'river', 4, 1.4]],
        },
      },
      {
        id: 'predio', type: 'fill', source: 'rs', 'source-layer': 'building', minzoom: 14,
        paint: { 'fill-color': c.predio, 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 14, 0, 15, 1] },
      },
      // vias: borda por baixo, miolo por cima
      {
        id: 'via-menor-borda', type: 'line', source: 'rs', 'source-layer': 'transportation', minzoom: 13,
        filter: ['in', ['get', 'class'], ['literal', menores]],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': c.viaBorda, 'line-width': largura(1.5, 16) },
      },
      {
        id: 'via-menor', type: 'line', source: 'rs', 'source-layer': 'transportation', minzoom: 12,
        filter: ['in', ['get', 'class'], ['literal', menores]],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': c.via, 'line-width': largura(0.6, 13) },
      },
      {
        id: 'via-secundaria', type: 'line', source: 'rs', 'source-layer': 'transportation', minzoom: 8,
        filter: ['in', ['get', 'class'], ['literal', secundarias]],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': c.via, 'line-width': largura(1, 18) },
      },
      {
        id: 'via-principal-borda', type: 'line', source: 'rs', 'source-layer': 'transportation', minzoom: 5,
        filter: ['in', ['get', 'class'], ['literal', principais]],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': c.viaPrincipalBorda, 'line-width': largura(2.4, 24) },
      },
      {
        id: 'via-principal', type: 'line', source: 'rs', 'source-layer': 'transportation', minzoom: 5,
        filter: ['in', ['get', 'class'], ['literal', principais]],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': c.viaPrincipal, 'line-width': largura(1.5, 20) },
      },
      {
        id: 'divisa-estado', type: 'line', source: 'rs', 'source-layer': 'boundary',
        filter: ['<=', ['get', 'admin_level'], 4],
        paint: { 'line-color': c.divisa, 'line-opacity': 0.45, 'line-width': 1.2, 'line-dasharray': [3, 2] },
      },
      {
        id: 'divisa-municipio', type: 'line', source: 'rs', 'source-layer': 'boundary', minzoom: 9,
        filter: ['==', ['get', 'admin_level'], 8],
        paint: { 'line-color': c.divisa, 'line-opacity': 0.18, 'line-width': 0.8, 'line-dasharray': [2, 2] },
      },
      {
        id: 'nome-rua', type: 'symbol', source: 'rs', 'source-layer': 'transportation_name', minzoom: 14,
        layout: { 'symbol-placement': 'line', 'text-field': NOME, 'text-font': FONTE, 'text-size': 11.5 },
        paint: { 'text-color': c.textoSuave, 'text-halo-color': c.halo, 'text-halo-width': 1.5 },
      },
      {
        id: 'nome-agua', type: 'symbol', source: 'rs', 'source-layer': 'water_name',
        layout: { 'text-field': NOME, 'text-font': ['Noto Sans Italic'], 'text-size': 12 },
        paint: { 'text-color': c.textoSuave, 'text-halo-color': c.halo, 'text-halo-width': 1.2 },
      },
      {
        id: 'nome-bairro', type: 'symbol', source: 'rs', 'source-layer': 'place', minzoom: 12,
        filter: ['in', ['get', 'class'], ['literal', ['suburb', 'neighbourhood', 'hamlet', 'quarter']]],
        layout: { 'text-field': NOME, 'text-font': FONTE, 'text-size': 12, 'text-max-width': 8 },
        paint: { 'text-color': c.textoSuave, 'text-halo-color': c.halo, 'text-halo-width': 1.5 },
      },
      {
        id: 'nome-vila', type: 'symbol', source: 'rs', 'source-layer': 'place', minzoom: 9,
        filter: ['==', ['get', 'class'], 'village'],
        layout: { 'text-field': NOME, 'text-font': FONTE, 'text-size': 12.5, 'text-max-width': 8 },
        paint: { 'text-color': c.texto, 'text-halo-color': c.halo, 'text-halo-width': 1.6 },
      },
      {
        id: 'nome-cidade', type: 'symbol', source: 'rs', 'source-layer': 'place',
        filter: ['in', ['get', 'class'], ['literal', ['city', 'town']]],
        layout: {
          'text-field': NOME,
          'text-font': FONTE_FORTE,
          'text-size': ['interpolate', ['linear'], ['zoom'], 6, ['match', ['get', 'class'], 'city', 13, 11], 12, ['match', ['get', 'class'], 'city', 19, 15]],
          'text-max-width': 8,
        },
        paint: { 'text-color': c.texto, 'text-halo-color': c.halo, 'text-halo-width': 1.8 },
      },
    ],
  }
}
