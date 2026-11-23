/**
 * Onde o app nativo guarda o refresh token.
 *
 * PENDENTE antes do primeiro build Android/iOS: trocar esta implementacao por um
 * plugin de armazenamento seguro (Keychain no iOS, Keystore no Android).
 * NAO usar @capacitor/preferences nem localStorage: ficam em texto puro no aparelho.
 *
 * Enquanto isso o token fica so em memoria: e seguro, mas o usuario precisa entrar
 * de novo cada vez que abre o app. Na web este modulo nao e usado (o cookie resolve).
 */
let emMemoria: string | null = null

export const cofre = {
  async ler(): Promise<string | null> {
    return emMemoria
  },
  async gravar(token: string): Promise<void> {
    emMemoria = token
  },
  async apagar(): Promise<void> {
    emMemoria = null
  },
}
