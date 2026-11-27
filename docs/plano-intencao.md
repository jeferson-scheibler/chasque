# Plano: o Chasque lembra por que você quis ir

Cada link salvo nasce de um motivo específico: um prato, uma vista, um show. Hoje esse motivo se perde.
A proposta é usar IA (Gemini) só para **ler** esse motivo no salvamento, devolvê-lo na hora do passeio e
conferir, depois da visita, se ele se confirmou. O perfil de gosto e as sugestões continuam sendo regras
nossas, explicáveis, em cima dos mesmos motivos (`lugares.Tag`) que as visitas já usam.

## Princípios

- **A IA lê e classifica; quem decide é o Chasque.** Nenhum lugar, nota ou sugestão é gravado só porque o
  modelo disse. Lugar identificado é sempre sugestão para a pessoa confirmar.
- **Mesma linguagem do perfil.** A IA só pode responder com os slugs de `Tag` que já existem (aconchegante,
  vista-bonita, cerveja-artesanal...). Assim o desejo (salvos) e a experiência (visitas) se comparam direto.
- **Nada do Instagram é baixado.** Continua valendo o que está em `salvos/instagram.py`: a entrada é só o
  texto que a pessoa colou ou escreveu (`Salvo.texto`), o @ do perfil e o tipo do link.
- **Privado por padrão.** A intenção é da pessoa. Ela nunca alimenta `MotivoComunidade`, que descreve o
  lugar por experiência real, e nunca aparece para pessoas de confiança.
- **Falhar em silêncio.** Se a IA cair, demorar ou errar, o app funciona como hoje.

## Fase 1: ler a intenção no salvamento

### Dados

Novo modelo `salvos.Intencao`, um para um com `Salvo` (apagar o salvo apaga a intenção):

| campo | o que guarda |
| --- | --- |
| `salvo` | OneToOne com `Salvo` |
| `estado` | `pendente`, `pronta`, `falhou`, `confirmada` (a pessoa aceitou ou editou) |
| `frase` | o motivo em até 120 caracteres, na voz da pessoa: "a pizza de fermentação natural" |
| `tags` | M2M com `lugares.Tag`, no máximo 3 |
| `lugar_nome`, `lugar_cidade` | o que o texto indica como lugar, em texto livre |
| `lugar_sugerido` | FK opcional para `Lugar`, preenchida pela **nossa** busca, nunca pelo modelo |
| `hash_entrada` | hash do texto enviado, para não chamar de novo se nada mudou |
| `modelo`, `versao_prompt` | para saber qual versão gerou o quê e reprocessar quando o prompt melhorar |
| `criado_em`, `atualizado_em` | |

`Usuario` ganha `usar_ia` (booleano, padrão `False`), no mesmo espírito de `contribuir_motivos`.

### Fluxo

1. A pessoa compartilha ou edita um salvo com texto. Se `usar_ia` estiver ligado e o hash mudou, a
   `Intencao` vai para `pendente`. Nada é chamado durante o request.
2. O comando `ler_intencoes` roda no serviço `leitor` (mesma imagem do `agendador`), a cada minuto, pegando
   as pendentes em lote pequeno. Sem Celery nem fila nova.
3. A chamada ao Gemini usa saída estruturada (JSON schema), com `tags` restritas a um enum dos slugs atuais.
4. Com `lugar_nome` e `lugar_cidade`, a mesma busca da tela de escolher lugar (com tolerância a erro de digitação e proximidade) procura na base do RS. Se houver um
   resultado claro, vira `lugar_sugerido`.
5. `estado = pronta`. O app mostra na próxima vez que a pessoa abrir o salvo.

### Prompt (rascunho)

Entrada: tipo do link, @ do perfil, texto colado, cidade base da pessoa e a lista de motivos (slug e nome).
Pede de volta:

```json
{
  "frase": "o que a pessoa quer viver ali, em até 120 caracteres, sem inventar nada fora do texto",
  "tags": ["até 3 slugs da lista, só os que o texto sustenta"],
  "lugar_nome": "nome do estabelecimento, ou vazio",
  "lugar_cidade": "cidade, ou vazio",
  "confianca": "alta | media | baixa"
}
```

Com `confianca` baixa, a frase não aparece. Fica só o pedido normal de "Por que quer ir".

### Telas

- **Link salvo (SalvoPage):** se houver `lugar_sugerido`, aparece no topo de `QualLugar` como "Parece ser o
  Tombado, em Lajeado", com um toque para confirmar. Os outros caminhos (novo Chasque, anexar) seguem iguais.
- **Por que quer ir:** a frase aparece preenchida e editável, com as tags como chips que dá para tirar.
  Editar ou aceitar marca `confirmada`.
- **Conta:** um interruptor "Usar IA para entender meus salvos", com uma linha dizendo o que vai para o
  Google e o que não vai.

### Custo e limites

- Modelo Flash do Gemini, configurado por `GEMINI_MODELO`; a chave fica em `GEMINI_CHAVE` no `.env`.
- Uma chamada por salvo com texto, repetida só se o texto mudar.
- Limite de 30 chamadas por pessoa por dia e timeout de 15 s.
- Reprocessar todos os salvos antigos é um comando à parte (`ler_intencoes --todos`), rodado à mão.

## Fase 2: o motivo volta na hora do passeio

- `RoteiroSerializer` passa a incluir `intencao` em cada parada: a frase do salvo mais recente daquele lugar com intenção `pronta` ou
  `confirmada`. Lugar com vários links usa o mais recente que tiver frase.
- **RoteiroPage:** abaixo do nome do lugar, "Você salvou pela pizza de fermentação natural."
- **Push do fim de semana (`agenda/push.py`):** se alguma parada tiver intenção, o aviso usa a mais
  específica, por exemplo "Sábado livre. Dá para ir comer aquela pizza que você salvou."
- **Opcional, depois:** `agenda/roteiros.py` pode usar as tags da intenção para escolher o momento do dia
  (café de manhã, música ao vivo à noite).

## Fase 3: conferir na visita

- Ao registrar visita de um lugar salvo (`/visita/nova?salvo=`), se houver intenção, a tela pergunta antes dos
  sóis: "Você foi pela vista. Valeu?", com as respostas *Valeu*, *Mais ou menos* e *Não*.
- `Registro` ganha `expectativa` (vazio, `sim`, `meio`, `nao`) e um FK opcional para a `Intencao`.
- `registros/perfil.py` ganha uma regra a mais, ainda explicável: as tags da intenção somam +0,5 com *Valeu*,
  0 com *Mais ou menos* e −0,5 com *Não*, além do que a nota já soma hoje.

Esse é o sinal que separa "o lugar é bom" de "o lugar é bom para o que eu procuro".

## Depois (fora deste plano)

- **Seu gosto:** tela que mostra o perfil em frases ("você salva muita vista, mas volta é nos aconchegantes"),
  com opção de apagar qualquer linha.
- **Dicas da internet:** Gemini com busca do Google, guardado por lugar (não por pessoa), com fonte e data.

## Testes

- O cliente do Gemini fica atrás de uma função (`salvos/ia.py`). Os testes trocam essa função por uma resposta
  fixa: nenhum teste chama a rede.
- Casos: tag fora da lista é descartada, mais de 3 tags corta, confiança baixa não mostra frase, hash igual
  não chama de novo, `usar_ia` desligado não chama, erro e timeout deixam `falhou` sem quebrar nada.
- Avaliação do prompt: umas 30 legendas reais (dos salvos da equipe), com as tags esperadas escritas à mão.
  O prompt só muda de versão se acertar mais nesse conjunto.

## Decisões em aberto

1. **IA ligada ou desligada por padrão?** O plano assume desligada, com convite para ligar no primeiro salvo
   com texto. Ligada por padrão pede aviso mais forte por causa da LGPD.
2. **Conta do Gemini:** na camada gratuita da API, o Google pode usar o conteúdo para melhorar os produtos.
   Para texto de usuário, o certo é a camada paga ou o Vertex AI.
3. **Reprocessar os salvos antigos** de quem ligar a IA, ou só os novos?

## Ordem de entrega

1. Modelo `Intencao`, `usar_ia` e o comando `ler_intencoes` com o cliente simulado e todos os testes.
2. Cliente real do Gemini e avaliação do prompt com as 30 legendas.
3. Telas da fase 1 (sugestão de lugar e frase editável) e o interruptor em Conta.
4. Fase 2 (roteiro e push).
5. Fase 3 (expectativa na visita e regra no perfil).
