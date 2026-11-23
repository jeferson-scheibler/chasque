# Chasque

App que guarda por que você gostou de cada lugar e usa isso para sugerir o próximo.
Identidade, missão, visão e valores: [docs/identidade.md](docs/identidade.md).
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
| GET | `/api/lugares/?q=&lat=&lng=` | Busca por nome (sem acento, tolera erro de digitação) e/ou proximidade. Até 20 resultados. |
| POST | `/api/lugares/` | Cadastra lugar que não está na base (`nome` + `cidade_id` ou `lat`/`lng`). 30 por dia por pessoa. |
| GET | `/api/cidades/` | Cidades importadas do OSM. |
| GET, POST | `/api/salvos/` | Lista os salvos (`?pendentes=1` só os sem lugar) ou recebe um compartilhamento (`url`, `text`, `title`). |
| GET, PATCH, DELETE | `/api/salvos/<id>/` | Ver, vincular a um lugar (`lugar_id`), anotar (`texto`) ou remover. |
| GET | `/api/lugares/<id>/` | Um lugar. |
| GET | `/api/tags/` | Motivos que dá para marcar numa visita, com o grupo (ambiente, preço, comida...). |
| GET, POST | `/api/registros/` | Visitas da pessoa (`?q=` busca no motivo, no lugar e na cidade) ou registra uma (`lugar_id`, `nota` 1 a 5, `ocasiao`, `tags`, `motivo`, `visitado_em`). |
| GET, PATCH, DELETE | `/api/registros/<id>/` | Ver, editar ou apagar uma visita. |
| GET | `/api/sugestoes/` | Lugares pelo gosto da pessoa (`?lat=&lng=` ou `?cidade_id=`, e `?ocasiao=`). Sem local, usa a cidade da pessoa ou a última visita. |
| GET, PUT | `/api/me/preferencias/` | Gostos escolhidos antes das visitas (`tags`). |
| GET | `/api/healthz` | Saúde da API e do banco. |

## Base de lugares (OpenStreetMap)

```bash
./scripts/importar-osm.sh
```

Baixa o arquivo do Sul do Brasil da Geofabrik (cerca de 430 MB, em `dados/`, fora do git) e importa, com o `osmium`:

- **Cidades:** os 497 municípios do RS (`importar_cidades`), com nome, código IBGE e a posição da sede
  (o membro `admin_centre` da relação do município no OSM). Outra UF: `--ibge 42` para SC, `41` para PR.
- **Lugares:** todo o RS (`importar_osm --relacao 242620`, recortado pelo contorno do estado no OSM):
  restaurantes, cafés, mirantes, vinícolas, cachoeiras, museus, hospedagem e outros. Cada lugar recebe a
  cidade do endereço ou a sede mais próxima. Sem `--relacao`, recorta pela caixa do Vale do Taquari (`--bbox`).

Pode rodar de novo: atualiza pelo id do OSM sem duplicar.
Os motivos iniciais de cada lugar (ex.: `vista-bonita`, `churrasco`, `aceita-pet`) saem das tags do OSM.

Os dados do OSM são ODbL: a atribuição "© colaboradores do OpenStreetMap" aparece na busca de lugares.

## Salvar lugares do Instagram

1. A pessoa compartilha um post, reel ou perfil do Instagram com o Chasque, ou cola o link no botão + de "Meus lugares".
2. A API guarda só o link, sem os parâmetros de rastreio (`igsh`, `utm_*`).
3. O app pergunta "Qual lugar é esse?" e busca na base. Se o lugar não existir, a pessoa cadastra com a cidade
   ou com a localização atual.

O Chasque não baixa a página do Instagram: os termos de uso dele proíbem coleta automatizada, e o Instagram
só manda o link no compartilhamento, sem legenda nem localização. A pessoa pode colar a legenda na anotação.

Onde o compartilhamento funciona hoje:
- **Android (Chrome):** com o Chasque instalado como app pelo menu "Adicionar à tela inicial", ele aparece no
  menu Compartilhar (Web Share Target). Exige HTTPS em produção.
- **iPhone e quem não instalou:** copiar o link no Instagram e colar no botão +.
- **Apps nativos (pendente):** intent filter no Android e Share Extension no iOS, quando os projetos do Capacitor forem criados.

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
- **Compartilhar no app nativo:** falta o intent filter do Android e a Share Extension do iOS.
- **Lugares cadastrados por usuários** entram na base comum sem moderação (só limite de 30 por dia). Revisar pelo admin.
- **Busca:** sem índice de texto por enquanto; com a base regional (alguns milhares de lugares) não faz falta.
  Para escalar, criar um índice trigram sobre `unaccent(nome)` com uma função imutável.
- **Produção:** trocar `runserver` por gunicorn atrás do nginx com HTTPS, `DJANGO_DEBUG=0`, `DRF_NUM_PROXIES=1`,
  cache compartilhado (Redis) para os limites de tentativa valerem entre processos, e servir `app/dist` como estático.
- **Tamanho do app:** o pacote do Ionic gera um arquivo JS de 1,1 MB (236 KB comprimido). Revisar quando houver telas reais.

## Próximas etapas

1. Mapa com MapLibre e tiles PMTiles próprios.
2. Enriquecer os motivos dos lugares com o que as pessoas marcam nas visitas (hoje vêm só do OSM).

## Registro de visita e perfil de gosto

Uma visita guarda o lugar, a nota (1 a 5 sóis), os motivos marcados, a ocasião, a data e um texto livre.
Exige pelo menos um motivo marcado ou escrito: o porquê é o que o Chasque guarda.

Cada visita alimenta o perfil de gosto (`PesoGosto`), recalculado a cada registro, edição ou exclusão:
a visita soma `(nota - 3) / 2` a cada motivo marcado, no geral e na ocasião. Nota 5 soma +1, nota 3 não
muda nada, nota 1 soma -1.

## Sugestões

Cada lugar num raio de 30 km soma o peso que a pessoa dá aos motivos que ele tem (`registros/sugestoes.py`):

- peso do motivo = perfil de gosto + 0,75 se a pessoa o escolheu nos primeiros gostos; com ocasião,
  vale o peso daquela ocasião mais metade do geral;
- motivo raro vale mais que comum: fator `1 + log10(total / lugares com o motivo) / 2`
  ("natureza" está em centenas de praças, "cerveja artesanal" em poucos lugares);
- salvos em "Quero conhecer" ganham +0,5; a distância desconta (a 10 km o lugar vale metade);
- lugares já visitados ficam de fora, e no topo vão no máximo 2 da mesma categoria.

Cada sugestão diz com o que combina. Sem visitas nem gostos, a tela pede os primeiros gostos.
