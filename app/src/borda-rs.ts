/**
 * Assinatura discreta: a divisa norte do Rio Grande do Sul (o Rio Uruguai, da Barra do Quaraí ao Rio Pelotas,
 * até Torres) achatada em poucos pixels, para virar a borda de cima de um cartão. Quem olha vê uma borda
 * levemente irregular; quem é daqui reconhece o desenho.
 */

// [longitude, latitude] de oeste para leste
const DIVISA_NORTE: [number, number][] = [
  [-57.61, -30.18], // Barra do Quaraí
  [-57.08, -29.76], // Uruguaiana
  [-56.55, -29.12], // Itaqui
  [-56.0, -28.66], // São Borja
  [-55.64, -28.18], // Garruchos
  [-55.13, -27.9], // Porto Xavier
  [-54.67, -27.57], // Porto Mauá
  [-54.1, -27.4],
  [-53.71, -27.19], // Barra do Guarita
  [-53.25, -27.18], // Iraí
  [-52.85, -27.25],
  [-52.3, -27.28], // Nonoai
  [-51.9, -27.46], // Marcelino Ramos
  [-51.67, -27.57], // Machadinho
  [-51.2, -27.95], // Rio Pelotas
  [-50.6, -28.25],
  [-50.07, -28.75], // São José dos Ausentes
  [-49.95, -29.02],
  [-49.73, -29.33], // Torres
]

/** Altura da borda em px: o desenho inteiro cabe nisso. */
export const ALTURA_DA_BORDA = 9

function caminho() {
  const lons = DIVISA_NORTE.map(([x]) => x)
  const lats = DIVISA_NORTE.map(([, y]) => y)
  const [x0, x1] = [Math.min(...lons), Math.max(...lons)]
  const [y0, y1] = [Math.min(...lats), Math.max(...lats)]
  const pontos = DIVISA_NORTE.map(([x, y]) => {
    const px = ((x - x0) / (x1 - x0)) * 100
    const py = ((y1 - y) / (y1 - y0)) * ALTURA_DA_BORDA
    return `${px.toFixed(2)},${py.toFixed(2)}`
  })
  return `M${pontos.join('L')}L100,${ALTURA_DA_BORDA + 1}L0,${ALTURA_DA_BORDA + 1}Z`
}

const svg =
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 ${ALTURA_DA_BORDA + 1}" preserveAspectRatio="none">` +
  `<path d="${caminho()}"/></svg>`

/** Para usar em `mask`/`-webkit-mask`: a faixa de cima com a divisa, o resto cheio. */
export const MASCARA_BORDA_RS =
  `url("data:image/svg+xml,${encodeURIComponent(svg)}") top / 100% ${ALTURA_DA_BORDA + 1}px no-repeat, ` +
  `linear-gradient(#000 0 0) bottom / 100% calc(100% - ${ALTURA_DA_BORDA}px) no-repeat`
