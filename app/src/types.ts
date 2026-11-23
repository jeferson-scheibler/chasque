export interface Lugar {
  id: number
  nome: string
  endereco: string
  cidade: string
  categoria: string
  categoria_nome: string
  lat: number
  lng: number
  aproximado: boolean
  fonte: 'osm' | 'overture' | 'usuario' | 'negocio'
  tags: string[]
  distancia_m: number | null
}

export interface Salvo {
  id: number
  origem: 'instagram'
  url: string
  tipo: 'post' | 'reel' | 'perfil'
  perfil: string
  texto: string
  lugar: Lugar | null
  criado_em: string
}

export interface Cidade {
  id: number
  nome: string
}

export interface Pagina<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export const NOME_DO_TIPO: Record<Salvo['tipo'], string> = {
  post: 'Post do Instagram',
  reel: 'Reel do Instagram',
  perfil: 'Perfil do Instagram',
}

/** "Café em Lajeado", "Café" ou "Lajeado", conforme o que o lugar tiver. */
export function resumoDoLugar(lugar: Lugar): string {
  if (lugar.categoria_nome && lugar.cidade) return `${lugar.categoria_nome} em ${lugar.cidade}`
  return lugar.categoria_nome || lugar.cidade
}
