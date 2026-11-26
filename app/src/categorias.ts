import {
  basketOutline, bedOutline, beerOutline, bonfireOutline, businessOutline, cafeOutline, colorPaletteOutline,
  eyeOutline, fastFoodOutline, filmOutline, flowerOutline, iceCreamOutline, leafOutline, libraryOutline,
  locationOutline, musicalNotesOutline, restaurantOutline, storefrontOutline, ticketOutline, trailSignOutline,
  waterOutline, wineOutline,
} from 'ionicons/icons'

// Categoria do OSM (chave=valor) -> ícone. O que não estiver aqui cai na chave (amenity, shop...) ou no pin.
const POR_CATEGORIA: Record<string, string> = {
  'amenity=cafe': cafeOutline,
  'shop=coffee': cafeOutline,
  'amenity=restaurant': restaurantOutline,
  'amenity=food_court': restaurantOutline,
  'amenity=fast_food': fastFoodOutline,
  'amenity=bar': beerOutline,
  'amenity=pub': beerOutline,
  'amenity=biergarten': beerOutline,
  'craft=brewery': beerOutline,
  'amenity=ice_cream': iceCreamOutline,
  'shop=bakery': storefrontOutline,
  'shop=pastry': iceCreamOutline,
  'shop=confectionery': iceCreamOutline,
  'shop=chocolate': iceCreamOutline,
  'amenity=nightclub': musicalNotesOutline,
  'amenity=cinema': filmOutline,
  'amenity=theatre': ticketOutline,
  'amenity=arts_centre': colorPaletteOutline,
  'tourism=gallery': colorPaletteOutline,
  'shop=art': colorPaletteOutline,
  'tourism=museum': libraryOutline,
  'tourism=viewpoint': eyeOutline,
  'tourism=attraction': trailSignOutline,
  'tourism=camp_site': bonfireOutline,
  'tourism=picnic_site': leafOutline,
  'leisure=garden': flowerOutline,
  'natural=waterfall': waterOutline,
  'waterway=waterfall': waterOutline,
  'leisure=water_park': waterOutline,
  'craft=winery': wineOutline,
  'shop=wine': wineOutline,
  'craft=distillery': wineOutline,
  'amenity=marketplace': basketOutline,
  'shop=farm': basketOutline,
  'shop=cheese': basketOutline,
}

const POR_CHAVE: Record<string, string> = {
  tourism: bedOutline,
  leisure: leafOutline,
  historic: businessOutline,
  shop: storefrontOutline,
}

export function iconeDaCategoria(categoria: string): string {
  if (POR_CATEGORIA[categoria]) return POR_CATEGORIA[categoria]
  const chave = categoria.split('=')[0] ?? ''
  // hotel, pousada, hostel... (o resto do tourism já foi tratado acima)
  return POR_CHAVE[chave] ?? locationOutline
}

/** "cafe-colonial" -> "café colonial" para mostrar os motivos do lugar. */
const NOMES_DAS_TAGS: Record<string, string> = {
  'ao-ar-livre': 'ao ar livre', 'vista-bonita': 'vista bonita', historico: 'história do lugar',
  economico: 'econômico', 'preco-justo': 'preço justo', 'vale-o-investimento': 'vale o investimento',
  'comida-caseira': 'comida caseira', 'cafe-colonial': 'café colonial', 'cafe-especial': 'café especial',
  'cerveja-artesanal': 'cerveja artesanal', vegetariano: 'opções vegetarianas',
  'atendimento-atencioso': 'atendimento atencioso', rapido: 'rápido', 'aceita-pet': 'aceita pet',
  acessivel: 'acessível', 'bom-para-criancas': 'bom para crianças', 'cultura-local': 'cultura local',
  'musica-ao-vivo': 'música ao vivo', 'cabe-grupo': 'cabe muita gente', 'produtor-local': 'produtor local',
}

export function nomeDaTag(slug: string): string {
  return NOMES_DAS_TAGS[slug] ?? slug.replace(/-/g, ' ')
}
