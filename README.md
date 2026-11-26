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
| GET | `/api/sugestoes/` | Lugares pelo gosto da pessoa (`?lat=&lng=` ou `?cidade_id=`, `?ocasiao=`, `?tipo=`, `?quando=&hora=`). Sem local, usa a cidade da pessoa ou a última visita. |
| GET, PUT | `/api/me/preferencias/` | Gostos escolhidos antes das visitas (`tags`). |
| GET | `/api/mapa/` | Os lugares da pessoa em GeoJSON (salvos e visitados, sem repetir). |
| GET | `/api/pessoas/` | Convite, pedidos recebidos e enviados, quem a pessoa segue e quem a segue. |
| POST | `/api/pessoas/convite/novo/` | Troca o código do convite (o link antigo para de funcionar). |
| GET, POST | `/api/convites/<codigo>/` | Ver de quem é o convite e pedir para seguir. |
| POST | `/api/confiancas/<id>/aceitar/` | Aceitar um pedido. |
| DELETE | `/api/confiancas/<id>/` | Recusar, cancelar, deixar de seguir ou remover seguidor. |
| GET | `/api/pessoas/<id>/visitas/` | Visitas que uma pessoa seguida liberou (`?ocasiao=`, `?boas=1`). |
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

## Mapa

O mapa é do próprio Chasque: um arquivo PMTiles do RS gerado do OpenStreetMap, sem Google nem servidor de
terceiros. Ninguém de fora fica sabendo onde as pessoas olham.

```bash
./scripts/gerar-mapa.sh
```

Recorta o RS pelo contorno do estado no arquivo da Geofabrik (`dados/osm/`) com o `osmium` e gera
`dados/mapa/rs.pmtiles` (cerca de 150 MB, zoom até 14) com o `tilemaker`, os dois do Debian, numa imagem
própria (`mapa/Dockerfile`). Leva uns 25 minutos e precisa de uns 5 GB livres durante a geração.

- **Entrega:** o serviço `mapa` do Compose (nginx) entrega o arquivo em `/tiles/`, atendendo pedidos parciais
  (Range): o app baixa só os pedaços da área na tela. Em desenvolvimento o Vite repassa `/tiles` para ele.
- **Estilo:** `app/src/mapa/estilo.ts`, nas cores da marca, com versão clara e escura.
- **Rótulos:** as fontes Noto Sans ficam em `app/public/mapa/fontes/` (do projeto Protomaps basemaps-assets, OFL).
- **Na tela:** visitados viram sóis ocre, e os que a pessoa quer conhecer, pontos Noite. Tocar abre um cartão
  com "Ver" e "Como chegar". A localização só é pedida quando a pessoa toca no botão.

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

1. Usar as visitas de pessoas de confiança nas sugestões ("a Ana amou e combina com você").

## Registro de visita e perfil de gosto

Uma visita guarda o lugar, a nota (1 a 5 sóis), os motivos marcados, a ocasião, a data e um texto livre.
Exige pelo menos um motivo marcado ou escrito: o porquê é o que o Chasque guarda.

Cada visita alimenta o perfil de gosto (`PesoGosto`), recalculado a cada registro, edição ou exclusão:
a visita soma `(nota - 3) / 2` a cada motivo marcado, no geral e na ocasião. Nota 5 soma +1, nota 3 não
muda nada, nota 1 soma -1.

## Pessoas de confiança

- **Só por convite:** cada pessoa tem um link (`/convite/<codigo>`). Quem abre pede para seguir, e a dona do link
  aceita ou recusa. Não há busca por nome ou e-mail, então ninguém descobre quem tem conta. Trocar o link
  invalida o antigo.
- **Visitas privadas por padrão:** cada visita tem "Quem pode ver": Só eu ou Pessoas de confiança.
  Quem segue vê só as liberadas, e só depois de aceito.
- **Não é recíproco nem transitivo:** seguir alguém não faz essa pessoa ver as suas visitas.
- **Busca reversa:** na página de quem você segue dá para filtrar por ocasião e pelas visitas de 4 e 5 sóis.
- Uma pessoa vê da outra só nome e iniciais, nunca o e-mail. Desfazer vale dos dois lados, sem aviso.

## Tela de entrada

A cena de Entrar e Criar conta é a ruína da igreja de São Miguel Arcanjo, nas Missões, em silhueta contra o sol
baixo: pelos arcos, janela e sineira passa a luz do céu, e araucárias perto e longe dão profundidade. Tudo fica no
alto de uma colina cujo contorno é a divisa norte inteira do RS, do extremo oeste a Torres, com a inclinação real;
o chão escuro se desfaz em degradê até a cor do formulário. O único movimento é o sol subindo atrás da torre.
Gerada por `marca/fonte/gerar_cena.py` (silhueta estilizada da ruína, araucárias de `araucaria.py`, divisa de
`gerar_borda.py`).

## Tela de abertura

Está no `index.html` (aparece antes do JavaScript): o contorno do símbolo se desenha, o sol acende e o nome
surge; `src/main.ts` tira a abertura depois de 1,9 s. Gerada por `marca/fonte/gerar_abertura.py` a partir dos
SVGs da marca.

## Mascote

Um cavalo crioulo baio, de crina azul-noite, lenço e pelego, aparece nos momentos em que a tela fala com a pessoa:

| Pose | Onde |
| --- | --- |
| empinando | Meus lugares vazio (boas-vindas) |
| trote | Visitados vazio; "Levando o recado..." ao receber um link compartilhado |
| espiando | Sugestões sem cidade escolhida (encosta na borda esquerda da tela) |
| duvida | Sugestões sem resultado, link compartilhado com erro, salvo que sumiu |
| parado | Pessoas de confiança vazio |
| aprovando | Depois de registrar uma visita nova |
| relinchando | Página não encontrada (qualquer endereço desconhecido, mesmo sem login) |

Uso: `<Mascote pose="aprovando" />`; as telas vazias passam a pose para `<Vazio>`. As cores são as mesmas nos dois
temas. No escuro, a crina e os cascos azul-noite sumiriam, então entra um contorno creme de adesivo em volta de
cada pose (camada `contorno`, transparente no claro). `src/components/Mascote.vue` é gerado por
`marca/fonte/gerar_mascote.py` a partir da folha `marca/original/Folha de Adesivos de Pôneis Fofos.png` (fundo
transparente; recorte por pose, separação pela paleta, suavização e potrace):

    docker run --rm -u $(id -u):$(id -g) -v $PWD:/c -w /c chasque-ferramentas python marca/fonte/gerar_mascote.py

`--previa PASTA` grava também as folhas claro e escuro em SVG.

Para pesar pouco, o gerador grava cada pose num arquivo próprio (`src/components/mascote/<pose>.ts`, com
coordenadas inteiras e relativas) e o `Mascote.vue` só guarda os tamanhos: a tela reserva o espaço na hora e
baixa o desenho da pose que mostra, de 2 a 5 KB comprimido (antes, as 7 poses juntas davam 81 KB).
`precarregarMascote(pose)` baixa antes, como faz a tela de visita com a comemoração.

## Motivos da comunidade

As visitas também descrevem os lugares para todo mundo, sem expor ninguém (`registros/comunidade.py`):

- contam só visitas de 4 ou 5 sóis (numa visita ruim os motivos respondem "o que não funcionou?");
- um motivo só passa a descrever o lugar a partir de **3 pessoas diferentes** (`MOTIVOS_MIN_PESSOAS`);
  abaixo disso daria para deduzir quem esteve lá;
- guarda só a contagem (`MotivoComunidade`), nunca quem marcou;
- quem desliga "Ajudar a descrever os lugares" na Conta sai da soma na hora; apagar visita ou conta também
  tira da soma;
- recalculado a cada visita; `python manage.py recalcular_motivos` refaz tudo (ex.: ao mudar o mínimo).

O aceite do cadastro explica isso (versão dos termos `2026-11-2`). Nas sugestões, um motivo confirmado
por pessoas vale 25% a mais e aparece como "Recomendado por N pessoas que foram".

## Sugestões

Cada lugar num raio de 30 km soma o peso que a pessoa dá aos motivos que ele tem (`registros/sugestoes.py`):

- peso do motivo = perfil de gosto + 0,75 se a pessoa o escolheu nos primeiros gostos; com ocasião,
  vale o peso daquela ocasião mais metade do geral;
- motivo raro vale mais que comum: fator `1 + log10(total / lugares com o motivo) / 2`
  ("natureza" está em centenas de praças, "cerveja artesanal" em poucos lugares);
- salvos em "Quero conhecer" ganham +0,5; a distância desconta (a 10 km o lugar vale metade);
- lugares já visitados ficam de fora, e no topo vão no máximo 2 da mesma categoria.
- com um tipo escolhido (Bar, Lanche, Restaurante, Café e doces, Vida noturna, Passeio), entram todos os
  lugares daquele tipo no raio, com ou sem motivos, e o gosto só ordena; já visitados também entram. Sem isso,
  um bar quase nunca apareceria: só 6% dos bares do RS têm algum motivo no OpenStreetMap.

Cada sugestão diz com o que combina. Sem visitas nem gostos, a tela pede os primeiros gostos.

### Evento ou grupo

A ocasião "Evento ou grupo" (`?ocasiao=grupo`; também dá para registrar visitas assim) procura lugar para muita
gente. O que um encontro grande pede soma ao gosto da pessoa:

- o motivo "Cabe muita gente" (`cabe-grupo`) pesa 1,5. Vem do OpenStreetMap quando o lugar tem `capacity` ou
  `seats` de 40 ou mais, ou é cervejaria, biergarten, praça de alimentação ou casa noturna, e das visitas, como
  qualquer motivo;
- ao ar livre (+0,4), música ao vivo e animado (+0,3) e churrasco (+0,2) ajudam; silencioso (-0,4) e
  aconchegante (-0,2), que costuma ser pequeno, descontam;
- com capacidade conhecida, soma até +0,6 (cheio a partir de 150 pessoas); com menos de 20, vale metade;
- cada pessoa que registrou visita de 4 ou 5 sóis como evento ou grupo no lugar soma +0,5 (até 3). Vale a
  regra dos motivos da comunidade: só a partir de 3 pessoas diferentes e só de quem ajuda a descrever os
  lugares, para ninguém descobrir quem foi e para uma conta sozinha não inflar o próprio bar.

As provas entram antes do desconto pela distância. A busca avalia no máximo os 400 lugares mais perto que
servem (no modo tipo, uma capital tem milhares de restaurantes no raio).

Cada resultado volta com `grupo: {capacidade, visitas}` e a tela mostra "Cabem umas 120 pessoas" ou "4 pessoas
fizeram encontro aqui e gostaram". A capacidade quase nunca está no OSM (cerca de 170 bares e restaurantes em todo o Sul):
o resto vem do tipo de lugar e das visitas. Junto com o tipo "Bar" e o dia, responde "bar para 30 pessoas
aberto na segunda".

### Quando: dia e horário

O filtro "Quando" (Hoje, Amanhã ou outro dia, e horário opcional) manda `?quando=AAAA-MM-DD&hora=HH:MM` para
`/api/sugestoes/`. Cada resultado volta com `horario.estado`:

- `aberto`: o `opening_hours` do OpenStreetMap confirma, e vem o horário do dia ("13:30 às 18:30");
- fechado: o OSM mostra fechado nesse dia ou hora, e o lugar sai da lista;
- `visto`: sem horário no OSM, mas 3 ou mais pessoas já registraram visita ali no mesmo dia da semana (só a
  contagem de pessoas, nas regras dos motivos da comunidade: quem desligou "Ajudar a descrever os lugares" não
  entra, e uma pessoa com várias visitas conta uma vez);
- `sem_info`: sem horário e sem visita; fica na lista com "confirme antes de ir" e, se houver, botão de ligar.

Lugares sem horário confirmado valem 15% menos na ordem. Sem hora escolhida, a madrugada da noite anterior
("Su 18:00-02:00") não faz a segunda contar como aberta; só uma virada que vai além das 06:00 conta. O horário é lido por `lugares/horarios.py`, que
entende os formatos comuns (dias, intervalos, "off", "24/7", madrugada, regras com `;` e com `,`) e responde
"não sei" para o resto (meses, nascer do sol, feriado sozinho). No RS, cerca de 9% dos lugares têm horário no
OSM e o interpretador entende 96% deles; o resto depende das visitas. Horário e telefone vêm na importação:
para atualizar, rode de novo o `importar_osm`.
