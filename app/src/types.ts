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
  /** Motivos marcados por pelo menos 3 pessoas em visitas boas. Só a contagem, nunca quem. */
  motivos_comunidade: { slug: string; pessoas: number }[]
  distancia_m: number | null
  telefone: string
}

/** Por que a pessoa salvou o link: lido pela IA (pendente, pronta) ou confirmado por ela. */
export interface Intencao {
  estado: 'pendente' | 'pronta' | 'confirmada'
  frase: string
  tags: string[]
  /** Lugar da base que o texto indica, quando não há dúvida. Some quando o salvo já tem lugar. */
  lugar_sugerido: Lugar | null
}

export interface Salvo {
  id: number
  origem: 'instagram'
  url: string
  tipo: 'post' | 'reel' | 'perfil'
  perfil: string
  texto: string
  lugar: Lugar | null
  visitado: boolean
  intencao: Intencao | null
  criado_em: string
  /** Só na resposta do POST: o link já estava na lista. */
  ja_salvo?: boolean
}

/** Lugar que a pessoa já tem: ligado a um link salvo ou com visita registrada. */
export interface MeuLugar extends Lugar {
  links: number
  visitado: boolean
}

export type Ocasiao = 'sozinho' | 'casal' | 'familia' | 'amigos' | 'trabalho' | 'grupo'

export interface Registro {
  id: number
  lugar: Lugar
  visitado_em: string
  ocasiao: Ocasiao
  nota: number
  tags: string[]
  motivo: string
  /** true: só a pessoa vê; false: pessoas de confiança também */
  privado: boolean
  criado_em: string
}

/** O que uma pessoa vê da outra: nome e iniciais, nunca e-mail. */
export interface Pessoa {
  id: number
  nome: string
  iniciais: string
}

export interface Motivo {
  slug: string
  nome: string
  grupo: string
  grupo_nome: string
}

/** Rótulo de cada nota, de 1 a 5 sóis. */
export const NOTAS = ['', 'Não gostei', 'Podia ser melhor', 'Foi ok', 'Gostei', 'Amei, voltaria sempre']

export interface Cidade {
  id: number
  nome: string
  lat: number
  lng: number
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

export type Momento = 'manha' | 'almoco' | 'tarde' | 'noite'

export const NOME_DO_MOMENTO: Record<Momento, string> = {
  manha: 'Manhã',
  almoco: 'Almoço',
  tarde: 'Tarde',
  noite: 'Noite',
}

export interface Parada {
  lugar: Lugar
  momento: Momento
  /** Veio da lista da pessoa; senão é uma sugestão do Chasque. */
  salvo: boolean
  salvo_id: number | null
  /** Por que a pessoa quis ir, do link salvo (lido pela IA ou confirmado). Vazio quando não há. */
  intencao: string
  horario: string
  km_da_anterior: number | null
}

export interface Roteiro {
  id: number
  dia: string
  cidade: string
  viagem: boolean
  visto: boolean
  paradas: Parada[]
}

export type EstadoAgenda =
  | { conectada: false }
  | { conectada: true; servico: string; lida_em: string | null; erro: string; dias_livres: string[] }
