# Chasque

App que guarda por que você gostou de cada lugar e usa isso para sugerir o próximo.
Projeto da disciplina GICN 2026B (Univates). Equipe: Jeferson S., Júlio Schneider e Weslley Panzer.

## Stack

| Parte | Tecnologia |
|---|---|
| API | Django 5.2 LTS, Django REST Framework, SimpleJWT |
| Banco | PostgreSQL 16 + PostGIS 3.5 |
| App (web, Android, iOS) | Vue 3, Ionic 9, Capacitor 8, Pinia, TypeScript, Vite |
| Infra | Docker Compose |

```
api/          Django
  chasque/    configuração (settings, urls)
  contas/     usuário, cadastro, login, sessão, exportar e excluir dados
  lugares/    Tag (motivos) e Lugar (com ponto geográfico)
  registros/  Registro (visita), PreferenciaDeclarada, PesoGosto (perfil)
app/          Vue + Ionic + Capacitor
  src/services/api.ts   cliente HTTP com renovação automática da sessão
  src/stores/sessao.ts  estado de login
  src/views/            telas
```

## Rodar em desenvolvimento

```bash
cp .env.example .env   # e troque DJANGO_SECRET_KEY e POSTGRES_PASSWORD
docker-compose up -d --build
```

- App: http://127.0.0.1:5180 (o Vite repassa `/api` para a API)
- API direta: http://127.0.0.1:8010/api/healthz
- Admin: http://127.0.0.1:8010/admin/

As portas só escutam em 127.0.0.1. Para abrir do seu computador, use um túnel SSH:

```bash
ssh -L 5180:127.0.0.1:5180 -L 8010:127.0.0.1:8010 usuario@vm
```

Criar um administrador:

```bash
docker-compose exec api python manage.py createsuperuser
```

## Testes

```bash
docker-compose run --rm api python manage.py test
```

```bash
docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp -v "$PWD/app":/app -w /app node:22-alpine npm test
```

## API

| Método | Caminho | O que faz |
|---|---|---|
| POST | `/api/auth/cadastro/` | Cria conta. Exige `aceita_termos: true`. |
| POST | `/api/auth/entrar/` | Login por e-mail e senha. |
| POST | `/api/auth/renovar/` | Troca o refresh por um access novo (refresh rotaciona). |
| POST | `/api/auth/sair/` | Invalida o refresh. |
| GET, PATCH | `/api/me/` | Dados da conta. |
| DELETE | `/api/me/` | Exclui a conta e os registros. Exige `senha`. |
| GET | `/api/me/exportar/` | Todos os dados da pessoa em JSON. |
| GET | `/api/healthz` | Saúde da API e do banco. |

## Decisões de segurança

- **Sessão na web:** o access token (15 min) fica só em memória. O refresh (30 dias) fica num cookie
  `httpOnly`, `SameSite=Lax`, limitado a `/api/auth/`. Um token que chegou por cookie só volta por cookie,
  então um script injetado na página não consegue ler o refresh.
- **Sessão no app nativo:** o app manda `X-Chasque-Cliente: mobile` e recebe o refresh no corpo, para guardar
  no armazenamento seguro do aparelho (ver pendências).
- **Refresh rotativo** com lista negra: cada renovação invalida o token anterior; sair e excluir a conta invalidam todos.
- **Senhas** com Argon2, mínimo de 10 caracteres e bloqueio de senhas comuns.
- **Limite de tentativas:** 10 logins por minuto e 5 cadastros por hora por IP.
- **Login** dá a mesma resposta para e-mail inexistente e senha errada.
- **LGPD:** consentimento guardado com data e versão dos termos; registros privados por padrão;
  exportação e exclusão real da conta.
- **Dados de terceiros:** do Google só o place ID pode ser guardado. Dados do OSM exigem atribuição.

## Pendências conhecidas

- **Armazenamento seguro no app nativo.** `app/src/services/cofre.ts` hoje guarda o refresh só em memória.
  Antes do primeiro build Android/iOS, trocar por um plugin de Keychain/Keystore (nunca `Preferences` nem `localStorage`).
- **Exportar dados no app nativo** precisa do plugin de arquivos/compartilhar. Na web já baixa o JSON.
- **Produção:** trocar `runserver` por gunicorn atrás do nginx com HTTPS, `DJANGO_DEBUG=0`, `DRF_NUM_PROXIES=1`,
  cache compartilhado (Redis) para os limites de tentativa valerem entre processos, e servir `app/dist` como estático.
- **Tamanho do app:** o pacote do Ionic gera um arquivo JS de 1,1 MB (236 KB comprimido). Revisar quando houver telas reais.
- **Identidade visual:** as cores do tema (`app/src/theme/variables.css`) são provisórias.

## Próximas etapas

1. Importar o recorte do OSM do Vale do Taquari (Geofabrik, filtro `amenity`, `tourism`, `shop`) com mapeamento de categoria para tags.
2. Registro de visita em até 3 toques e lista pessoal com busca por motivo.
3. Onboarding de gostos (`PreferenciaDeclarada`) e primeira sugestão por tags, ocasião e distância.
4. Mapa com MapLibre e tiles PMTiles próprios, e build PWA.
