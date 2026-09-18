# netlab-g1-scraper

## Diagnóstico

O código legado (`legacy/scraper_original.py`) roda sem erro e produz um CSV
vazio. A causa raiz não é um bug de programação: o conteúdo da busca no G1
é inserido via JavaScript, então o HTML devolvido por `requests.get()` nunca
contém os resultados nem a palavra "lgpd" — os seletores (`div.resultado`
e afins) simplesmente não têm o que encontrar. Essa falha silenciosa mascarou
uma segunda camada de bugs internos, que também precisavam de correção e só se
manifestariam se a fonte de dados voltasse a funcionar.

### Baseline (evidência)

Execução do código original registrada antes de qualquer alteração:
`page=0..4` retornam HTTP 200, HTML idêntico (57992 bytes) em todas as
páginas, zero ocorrências de "lgpd", zero `div.resultado`, CSV gerado só com
cabeçalho, nenhuma exceção lançada.

### Duas hipóteses descartadas

- **User-Agent:** requisição com UA padrão do `requests` e com UA de
  navegador retornam resposta idêntica — não é bloqueio por identificação do
  cliente.
- **Paginação `page=0`:** o parâmetro `page=N` da URL é ignorado pelo
  site; `page=0`, `page=1` e `page=2` produzem sempre a mesma resposta.
  A paginação real do G1 é por rolagem infinita, incrementando um offset
  (`from`) de 10 em 10 — não pela URL.

### Bugs internos (independentes do site)

Corrigidos na rotina nova independentemente da mudança de fonte, pois
quebrariam mesmo com o site intacto:

- lista de resultados sobrescrita a cada página (perde todas as páginas
  menos a última) em vez de acumulada;
- ausência de `timeout`, verificação de status HTTP e `try/except` —
  bloqueio, erro de servidor ou queda de conexão são tratados como sucesso
  ou derrubam a execução;
- URL montada por concatenação, sem *URL encoding*;
- rotina inteira disparada no nível do módulo, sem `if __name__ ==
  "__main__":`, impedindo testar funções isoladamente;
- requisição, parsing e gravação amontoados numa única função, sem
  separação testável;
- número fixo de páginas, sem condição de parada vinda da resposta;
- único log é um `print`, sem níveis nem arquivo, com mensagem final
  ("Coleta finalizada.") exibida mesmo com zero registros salvos;
- pausa fixa entre requisições curta demais para um portal de grande
  porte;
- nomes de campos duplicados no código (dicionário do registro e
  `fieldnames` do CSV), fonte de inconsistência silenciosa.

### Problemas mascarados

Nunca deram sintoma porque o laço original nunca encontrou nenhum card, mas
apareceriam assim que a coleta voltasse a funcionar — a mudança de fonte
(HTML → API) altera a forma de alguns deles, não a existência:

- encadeamento que quebra com um único campo ausente no card;
- CSV sem `encoding="utf-8"` nem `newline=""` (corrompe acentos e insere
  linhas em branco no Windows);
- sem `strip()` nem deduplicação dos registros;
- URL do card sem normalização (pode vir relativa ou como link de
  rastreamento);
- timestamp de coleta sem fuso horário;
- data de publicação gravada como texto bruto, sem normalização;
- arquivo de saída com nome fixo, sobrescrito a cada execução.

### Conclusão do diagnóstico

A causa da falha é 100% mudança no site (conteúdo servido via JavaScript,
não HTML estático) — não há bug do lado do cliente que a explique sozinho.
Ainda assim, o código continha bugs internos reais, que exigiam correção
independente da mudança de fonte. Detalhamento item a item (evidências,
trechos de código e status de cada um) na seção 6 de `docs/diagnostico.md`.

## Justificativa da coleta via API

O enunciado descreve a rotina original usando Beautiful Soup sobre o HTML da
página de busca. O diagnóstico (seção anterior) mostrou que essa premissa não
se sustenta mais: os resultados não existem no HTML recebido por
`requests` — são inseridos no DOM via JavaScript, depois que o navegador
executa uma chamada à API interna do site.

### A fonte real dos dados

`POST https://busca.globo.com/v1/search`, que devolve JSON e não exige
cookies. Identificada inspecionando as requisições de rede feitas pelo
próprio navegador ao carregar a busca por "lgpd" — não documentada
publicamente, mas de acesso livre.

- Corpo da requisição (é uma **lista**, não um objeto — enviar objeto solto
  produz HTTP 400):
```json
  [{"search_profile": "sp_g1_globo_com", "query": "g1.info_query_recency",
    "params": {"q": "lgpd", "from": 0, "size": 10}}]
```
- Cabeçalhos mínimos exigidos: `x-tenant-id: g1`, `origin:
  https://g1.globo.com`, `x-track-urls` (só a presença importa, o valor
  não).
- Resposta: `dados[0]["result"]["hits"]["hits"]`, cada hit com `_source`.
- Paginação real: o parâmetro `page=N` da URL usado no código legado é
  ignorado pelo site; o incremento real é no `from` do corpo da requisição,
  de 10 em 10, com `size=10` fixo (igual ao comportamento do site).

### Por que manter a coleta via API em vez de forçar o caminho HTML

- **Fidelidade ao problema real.** O desafio pede uma rotina que funcione
  contra o G1 hoje. Insistir em Beautiful Soup sobre HTML estático
  reproduziria a mesma falha (coleta vazia) que o diagnóstico já explica.
- **Dado estruturado e completo.** A API devolve todos os campos da matéria
  em JSON (`title`, `url`, `issued`, `modified`, corpo do resumo via
  `highlight`, etc.), sem depender de seletores CSS frágeis e sujeitos a
  mudança de layout — o mesmo tipo de fragilidade que causou a falha
  original.
- **Sem dependência de JavaScript no cliente.** Não é necessário um
  navegador headless (Selenium/Playwright) para renderizar a página; uma
  requisição HTTP simples ao mesmo endpoint que o navegador usa já basta.

### O que isso muda em relação ao enunciado

O enunciado menciona Beautiful Soup como parte da rotina original. Ele
continua tendo um papel real na solução — limpeza de tags HTML embutidas nos
fragmentos de `highlight` retornados pela API (ver seção "Papel do Beautiful
Soup") —, só que deixa de ser a ferramenta de extração principal, porque não
há mais HTML de página a parsear. Essa mudança de abordagem é a decisão
técnica central do projeto e está registrada, com toda a evidência de rede
que a sustenta, em `docs/diagnostico.md`.

## Decisões técnicas

Resumo das decisões estruturais do projeto, com o motivo de cada uma. O
detalhamento de decisões específicas de dados está nas seções seguintes
(dicionário de dados, Beautiful Soup, limitações).

### Organização do código

- **Layout `src`** com Poetry: código em `src/g1_scraper/`, testes
  importando o pacote instalado — evita que os testes acidentalmente
  dependam do diretório de trabalho em vez do pacote real.
- **Separação por responsabilidade**, um módulo por preocupação
  (`models.py`, `config.py`, `client.py`, `parser.py`, `dedup.py`,
  `storage.py`, `scraper.py`, `__main__.py`) — é o que torna o parsing e a
  deduplicação testáveis sem rede nem efeito colateral em disco (ver seção
  de testes).
- **`legacy/scraper_original.py` permanece intocado.** O código original é
  preservado como está, para comparação e como evidência do diagnóstico —
  não é refatorado nem corrigido no lugar.
- **Scripts de inspeção** (usados para investigar a API e a paginação) ficam
  em `scripts/`, separados do pacote principal; evidências brutas dessa
  investigação em `data/baseline/`.

### Qualidade e versionamento

- **Conventional Commits**, um módulo/arquivo por commit sempre que possível
  — facilita rastrear quando e por que cada decisão entrou.
- **Ruff** para lint e formatação, excluindo `legacy/` (o código original não
  é reformatado).
- **pytest** para os testes automatizados.
- **`.gitignore` não ignora `data/output/` nem `data/reference/`** — saídas
  de teste não são versionadas, mas a base final da coleta entrou por `git
  add` explícito, como evidência de execução real.

### Ambiente

- **Python 3.12** (o padrão da máquina é 3.15 alpha — não usado, por ser
  versão de teste); `.venv` in-project.
- **Dependências de produção:** `requests`, `beautifulsoup4`, `tzdata`.
  `tzdata` é necessário especificamente **no Windows**, onde `zoneinfo` não
  encontra a base de fusos horários IANA do sistema operacional — sem essa
  dependência, `ZoneInfo("America/Sao_Paulo")` levanta
  `ZoneInfoNotFoundError`. Registrado na seção de instalação abaixo.

### Decisões sobre o escopo da coleta

- **Anúncios são excluídos da base** (identificados pelo campo
  `pubeditorial`, que é um objeto quando presente — não um booleano).
  Decisão de escopo: o desafio pede resultados da busca por "LGPD", e
  anúncios não são resultado de busca.
- **Deduplicação pela URL real, nunca pelo título** — existem matérias com
  títulos quase idênticos e URLs diferentes; deduplicar por título
  descartaria registros legítimos.
- **Página com falha não derrota a coleta inteira:** a falha é contada e a
  coleta segue; só um número de falhas consecutivas configurável interrompe
  a execução. Isso pode deixar um buraco silencioso na base, por isso o
  número de páginas com falha entra nas métricas e no manifesto de cada
  execução.
- **Registro sem URL real é mantido na base**, mas fica fora da
  deduplicação e é contado à parte — descartar silenciosamente perderia
  dado sem necessidade.

## Estrutura do repositório

```
.
├── src/
│   └── g1_scraper/
│       ├── __init__.py
│       ├── __main__.py       # CLI (argparse), logging, resumo final, exit code
│       ├── models.py         # dataclass Resultado (fonte única dos campos)
│       ├── config.py         # contrato da API, Config, corpo_consulta()
│       ├── client.py         # sessão HTTP, timeout, retries, raise_for_status
│       ├── parser.py         # extração tolerante dos campos a partir do hit
│       ├── dedup.py          # deduplicação pela URL real
│       ├── storage.py        # gravação CSV/JSON + manifesto da execução
│       └── scraper.py        # laço de paginação, condições de parada, métricas
├── legacy/
│   └── scraper_original.py   # código original, preservado intocado
├── scripts/
│   ├── baseline.py                        # execução do código legado (evidência)
│   ├── inspecao_ua.py                     # teste da hipótese de User-Agent
│   ├── inspecao_url.py                    # inspeção da estrutura da página / API
│   ├── inspecao_api.py                    # mapeamento do contrato da API
│   ├── inspecao_paginacao.py              # mecanismo real de paginação (from/size)
│   ├── inspecao_paginacao_size.py         # variação do parâmetro size
│   ├── inspecao_paginacao_fim.py          # comportamento no fim do conjunto (from=1219+)
│   ├── inspecao_paginacao_estabilidade.py # estabilidade dos resultados entre repetições
│   ├── snapshot_referencia.py             # geração dos snapshots de referência (16/09)
│   └── avaliacao_qualidade.py             # cálculo das sete dimensões de qualidade
├── tests/
│   ├── conftest.py            # fixtures a partir de hits reais de snapshot_from_0.json
│   ├── fixtures/
│   ├── test_smoke.py
│   ├── test_parser.py
│   ├── test_dedup.py
│   ├── test_client.py
│   ├── test_storage.py
│   ├── test_scraper.py
│   └── test_cli.py
├── data/
│   ├── baseline/
│   │   ├── html/               # HTML bruto do código legado (page_0..4, testes de UA)
│   │   ├── api/                 # respostas brutas da API usadas na investigação
│   │   └── g1_lgpd.csv          # saída (vazia) do código legado
│   ├── reference/
│   │   ├── amostra_manual.csv         # 30 primeiros cards, coletados no navegador
│   │   └── snapshot_from_{0,10,20}.json  # snapshots da API de 16/09
│   └── output/
│       ├── g1_lgpd_20260917T204713.{csv,json}   # base final da coleta
│       ├── manifesto_20260917T204713.json        # manifesto da execução final
│       └── coleta_20260917T204713.log            # log DEBUG da execução final
├── docs/
│   ├── diagnostico.md              # inclui a triagem de bugs (B/M/S)
│   ├── avaliacao_qualidade.md
│   ├── metricas_qualidade.json
│   └── proposta_llm.pdf        
├── pyproject.toml
├── poetry.lock
└── README.md
```

## Requisitos e instalação

### Requisitos

- Python 3.12 (o `python` padrão da máquina pode apontar para 3.15 alpha —
  confirme a versão antes de criar o ambiente, não é usada neste projeto).
- [Poetry](https://python-poetry.org/) para gerenciamento de dependências e
  ambiente virtual.
- Windows: pacote `tzdata` (listado como dependência de produção) é
  obrigatório — sem ele, `zoneinfo` não encontra a base de fusos horários
  IANA no sistema operacional, e `ZoneInfo("America/Sao_Paulo")` levanta
  `ZoneInfoNotFoundError`. Em Linux/macOS a base já costuma vir do sistema,
  mas manter a dependência não causa problema.

### Instalação

Com Poetry (recomendado — cria e gerencia o `.venv` automaticamente):

```bash
git clone https://github.com/camazlucas/netlab-g1-scraper.git
cd netlab-g1-scraper
poetry env use 3.12
poetry install
```

Alternativa com `pip` (ambiente virtual manual):

```bash
git clone https://github.com/camazlucas/netlab-g1-scraper.git
cd netlab-g1-scraper
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -e .
```

## Execução

Rodar a partir da raiz do repositório, com o ambiente ativado (ou via
`poetry run`):

```bash
python -m g1_scraper
```

Isso coleta os resultados de "lgpd" (termo padrão), gera CSV e JSON em
`data/output/`, junto com um log da execução (`coleta_<timestamp>.log`) e um
manifesto (`manifesto_<timestamp>.json`) com data, commit, parâmetros e
versões usadas.

### Argumentos disponíveis

| Argumento | Padrão | Descrição |
|-----------|--------|-----------|
| `--termo` | `lgpd` | termo buscado |
| `--size` | `10` | itens por página (mesmo valor usado pelo site) |
| `--max-paginas` | `200` | trava de segurança para o número de páginas |
| `--pausa` | `1.5` | segundos de espera entre páginas |
| `--formato` | `ambos` | `csv`, `json` ou `ambos` |
| `--dir-saida` | `data/output/` | diretório onde os arquivos são gravados |
| `-v`, `--verboso` | desligado | log em nível DEBUG (console e arquivo) |

### Exemplos

```bash
# coleta rápida de teste, só 2 páginas
python -m g1_scraper --max-paginas 2 -v

# buscar outro termo, salvando só em JSON
python -m g1_scraper --termo "vazamento de dados" --formato json

# coleta completa (comportamento usado na entrega final)
python -m g1_scraper -v
```

### Código de saída

`0` se ao menos um registro foi salvo; `1` se a base ficou vazia — sinaliza
falha para scripts ou pipelines que chamem a coleta, em vez da mensagem
genérica "Coleta finalizada." do código original mesmo com zero resultados.

## Testes

Suíte com **52 testes automatizados** (`pytest`), sem dependência de rede —
toda chamada HTTP é mockada (`monkeypatch`) ou usa fixtures de arquivo/dicionário.

```bash
poetry run pytest -v
```

### Cobertura por arquivo

| Arquivo | Cobre | Testes |
|---------|-------|--------|
| `test_smoke.py` | sanity check do pacote instalado | 1 |
| `test_parser.py` | resumo (matéria normal/ausente/vídeo), datas ausentes, `eh_anuncio`, `extrair_url_real` (com e sem `u=`), `normalizar_data` (Z vs. offset) | 12 |
| `test_dedup.py` | URL repetida descartada, chave normaliza só esquema/domínio, títulos quase iguais com URLs diferentes não fundidos, registro sem URL mantido e contado | 5 |
| `test_client.py` | timeout, `ConnectionError`, status não retentáveis (400, 403) sem retry, status retentáveis (429, 500) com retry, esgotamento de tentativas | 9 |
| `test_storage.py` | `agora`/`carimbo` com fuso, `caminho_saida`, CSV/JSON com acentos, `hash_commit` com falha do git, `versoes()`, estrutura do manifesto | 9 |
| `test_scraper.py` | acumulação entre páginas, parada por hits ausente/fim do total/teto da API, falhas isoladas vs. consecutivas, deduplicação agregada nas métricas | 7 |
| `test_cli.py` | código de saída (0/1), formatos csv/json/ambos, argumentos customizados no `Config`, `resumir()` | 9 |

### Fixtures

`tests/conftest.py` deriva as fixtures de hits **reais** de
`data/reference/snapshot_from_0.json` — uma matéria normal, um vídeo e um
anúncio (com `pubeditorial` de verdade) — em vez de dados sintéticos. As
variantes de campo ausente (`hit_sem_highlight`, `hit_sem_issued`,
`hit_sem_modified`) são cópias da matéria normal com uma chave removida, para
exercitar a tolerância do parser a campos faltantes.

`client.py`, `scraper.py` e `__main__.py` são testados com as dependências
mockadas (isolamento por módulo); `parser.py`, `dedup.py` e `storage.py`
rodam a lógica real contra dados/arquivos de teste (`tmp_path`).

## Resultado da avaliação de qualidade

A base final (`data/output/g1_lgpd_20260917T204713.csv`, coletada em
17/09/2026 20:47 — 1015 registros, 122 páginas, 0 falhas) foi comparada com
duas referências independentes de 16/09/2026: a amostra manual coletada no
navegador e os snapshots da API do mesmo momento (30 itens, 25 sem anúncio em
cada). O casamento é feito pela URL real. Metodologia completa, ressalvas e
números por campo em `docs/avaliacao_qualidade.md` e `docs/metricas_qualidade.json`.

| Dimensão | Resultado |
|----------|-----------|
| Precisão | 25/25 (100%) em ambas as referências |
| Acurácia | `titulo`, `resumo`, `data_atualizacao` — 25/25 (100%) |
| Unicidade | 0 duplicatas na base final (6 descartadas de 1021 brutos) |
| Completude | 100% em 7 de 8 campos; `resumo` = 1014/1015 (99,9%) |
| Consistência | `url`, `pagina`, `posicao`: 100%; datas: 1011/1015 (99,6%) pelo critério de offset fixo — ver ressalva |
| Atualidade | Intervalo de 27,6h entre coletas; publicações de 2010–2026, idade média ≈ 1088 dias |
| Rastreabilidade | 1015/1015 (100%), manifesto com commit registrado |
| Vazamento de anúncios | 0/10 |
| Teste de contagem | 1021 registros brutos + 198 anúncios = 1219 = `hits.total.value` — confere |

### Duas ressalvas sobre os números acima

- **`resumo` ausente em 1 registro não é falha do parser.** O hit (página 43,
  posição 7) volta da API sem `highlight` e sem `description` — as duas
  fontes previstas pelo parser. O site monta um resumo nesse caso por um
  mecanismo próprio do frontend, sem campo estruturado correspondente na
  resposta da API. Decisão: manter o parser como está, `resumo` sai vazio.
- **Os 4 registros "inconsistentes" em data são notícias antigas (2010–2015)
  com offset `-02:00`**, do horário de verão que o Brasil usou até 2019 —
  `ZoneInfo("America/Sao_Paulo")` aplica isso corretamente. O critério de
  consistência assumiu offset fixo `-03:00`; a conversão de fuso em si está
  100% correta.

## Dicionário de dados

8 colunas, na ordem gravada no CSV/JSON (definida por `Resultado` em `models.py`,
fonte única — não duplicada em `storage.py`).

| Campo | Tipo | Origem no hit | Exemplo |
|-------|------|----------------|---------|
| `titulo` | `str \| None` | `_source.title`, com espaços/quebras colapsados | `"LGPD: o que muda para as empresas em 2026"` |
| `url` | `str \| None` | `_source.url` é link de rastreamento; a URL real é decodificada do parâmetro `u=`. Chave de deduplicação | `"https://g1.globo.com/economia/noticia/2026/..."` |
| `resumo` | `str \| None` | Fragmentos de `highlight.body`, com `<em>` removido via Beautiful Soup, cada um entre reticências (`...`) e unidos por `" — "`; alternativa: `_source.description` (sem reticências), usada nos hits de vídeo; `None` se nenhuma das duas fontes vier no hit | `"...a Lei Geral de Proteção de Dados... — ...entrou em vigor em..."` |
| `data_publicacao` | `str \| None` (ISO 8601) | `_source.issued`, convertido para o fuso `America/Sao_Paulo` | `"2026-09-15T08:30:00-03:00"` |
| `data_atualizacao` | `str \| None` (ISO 8601) | `_source.modified`, convertido para o fuso `America/Sao_Paulo` — **é este campo, não `issued`, que o G1 exibe no card** | `"2026-09-16T14:12:00-03:00"` |
| `pagina` | `int` | `from // size` da requisição, base 0 | `0` |
| `posicao` | `int` | Posição do hit na página, base 1, **contada antes do filtro de anúncios** — espelha a posição exibida no site | `3` |
| `coletado_em` | `str` (ISO 8601) | Instante único da execução inteira, com fuso explícito | `"2026-09-17T20:47:13-03:00"` |

### Notas

- **`data_publicacao` vs. `data_atualizacao`:** o card do G1 mostra a data de
  *atualização* (`modified`), não a de publicação original (`issued`). A base
  grava os dois campos separadamente, para não perder a distinção.
- **Reticências e `" — "` no `resumo` são dado, não formatação de exibição:**
  reproduzem exatamente o que o site mostra no card, o que permite comparar o
  campo por igualdade exata contra a amostra de referência.
- **Data ISO "naive" (sem fuso) vira `None`**, em vez de assumir um fuso —
  evita gravar um horário ambíguo como se fosse confiável.
- Datas de notícias anteriores a 2019 podem sair com offset `-02:00` em vez
  de `-03:00`: é o horário de verão que o Brasil usava até então, aplicado
  corretamente pelo `zoneinfo` — não é bug (ver seção de limitações).

## Papel do Beautiful Soup

O enunciado do desafio menciona Beautiful Soup como parte da rotina original,
usado para parsing do HTML da página de busca. Esse caminho deixou de existir:
a seção de diagnóstico mostra que os resultados não estão no HTML recebido
por `requests` — são inseridos via JavaScript a partir de uma API que devolve
JSON diretamente.

Isso não tornou a biblioteca dispensável, só mudou onde ela atua. O único
HTML que passa pelo pipeline da solução nova é um payload pequeno e
localizado: os fragmentos de `highlight.body` que a API devolve para compor o
resumo de cada resultado vêm com o termo buscado destacado em tags `<em>`
(por exemplo, `"a <em>lgpd</em> entrou em vigor"`). `parser.py` usa
`BeautifulSoup(frag, "html.parser").get_text()` para remover essas tags e
decodificar entidades HTML, extraindo só o texto — é o único ponto do projeto
onde há HTML de verdade para interpretar, e é justamente o campo que alimenta
`resumo`.

Não há mais parsing de página inteira, seletores CSS (`div.resultado` e
afins) ou navegação pela árvore do documento — só limpeza de um fragmento de
texto pontual, sobre um dado que já chega estruturado em JSON.

## Limitações

- **Dependência de uma API não documentada publicamente.** O endpoint
  `busca.globo.com/v1/search`, o formato do corpo da requisição e os
  cabeçalhos mínimos foram descobertos por engenharia reversa das requisições
  do navegador, não por documentação oficial — o contrato pode mudar sem
  aviso.
- **Ausência do Beautiful Soup no caminho principal de coleta.** O enunciado
  original previa parsing de HTML de página inteira; a solução usa a
  biblioteca só para limpar tags `<em>` dos fragmentos de `highlight` (ver
  seção anterior).
- **Anúncios são excluídos da base por decisão de escopo** (identificados
  pela presença de `pubeditorial` no hit) — não é resultado de busca, mas é
  uma escolha, não uma limitação técnica da coleta.
- **Teto de paginação da API:** `from + size` não pode ultrapassar 10000
  (a API responde HTTP 400 acima disso). Não afetou a coleta de "lgpd"
  (1219 resultados no total), mas limita buscas por termos muito mais
  frequentes.
- **`max_score` varia entre execuções**, mesmo sem mudança perceptível nos
  resultados — o perfil de busca usado pelo G1 pondera recência, então o
  score não é estável no tempo.
- **Amostra de referência limitada a 30 itens** (25 sem anúncio). Suficiente
  para validar o comportamento do parser, mas pequena para detectar casos
  raros — o próprio registro sem `resumo` (1 em 1015) não teria aparecido
  numa amostra de 25.
- **Datas relativas na amostra manual** ("há 1 dia") foram convertidas a
  partir de `coletado_em`, com tolerância — não são um timestamp exato
  capturado no momento da coleta manual.
- **Deriva do ranking do G1 entre execuções.** Em 24h, um item saiu do topo
  da busca, anúncios trocaram de posição e um item mudou de página. Por isso
  a avaliação de qualidade final comparou a coleta contra os snapshots de
  16/09 (capturados no mesmo momento da amostra manual), não contra uma nova
  amostra refeita no dia da coleta final — a deriva é documentada como
  fenômeno observado, não tratada como erro.
- **Um hit sem `highlight` nem `description`** sai com `resumo` vazio
  (1 registro em 1015 na coleta final) — as duas fontes previstas pelo parser
  não vêm no hit; o site, nesse caso, monta o card por um mecanismo próprio do
  frontend sem campo estruturado correspondente na resposta da API.
- **Offset `-02:00` em datas antigas** (notícias de antes de 2019, cobertas
  pelo horário de verão histórico do Brasil) é conversão correta do
  `zoneinfo`, não um bug — mas some do critério simplificado de consistência
  da avaliação de qualidade se não for explicado (ver seção de resultados).

## Extensões futuras

- **Agendamento da coleta** (cron, GitHub Actions ou similar), rodando
  periodicamente sem intervenção manual.
- **Monitoramento contínuo do contrato da API** — como o endpoint não é
  documentado publicamente, um teste automatizado que rode a coleta contra
  a API ao vivo periodicamente detectaria mudanças de schema ou de
  comportamento antes que afetassem a coleta de produção.
- **Fallback com navegador headless** (Playwright/Selenium) caso a API deixe
  de funcionar ou passe a exigir algo que uma requisição simples não
  reproduz (ex.: um token gerado por JavaScript no cliente).
- **Armazenamento em banco de dados**, em vez de arquivos CSV/JSON, para
  consultas e agregações entre execuções.
- **Coleta incremental**, salvando só registros novos desde a última
  execução (por `url` ou `data_atualizacao`), em vez de recoletar a base
  inteira a cada vez.
- **As outras cinco propostas de uso de LLM levantadas na etapa 9** (não
  escolhidas) também são extensões naturais:
  - comparação de snapshots (schema diff) para localizar a causa de uma
    queda de coleta;
  - sugestão de novo mapeamento de campos a partir de um diff de schema
    confirmado;
  - geração de casos de teste a partir de uma fixture real;
  - classificação de severidade de anomalia, para evitar fadiga de alerta;
  - resumo executivo do manifesto de cada execução.


## Documentação adicional

- [`docs/diagnostico.md`](docs/diagnostico.md) — narrativa completa do
  diagnóstico: ambiente do baseline, execução do código legado, evidências
  por página, revisão do código original (triagem B/M/S), estrutura atual da
  página, mecanismo de paginação e amostra de referência.
- [`docs/avaliacao_qualidade.md`](docs/avaliacao_qualidade.md) — metodologia
  e resultado das sete dimensões de qualidade, com as ressalvas sobre os
  números.
- [`docs/metricas_qualidade.json`](docs/metricas_qualidade.json) — números
  brutos por campo e por registro pareado, usados na avaliação acima.
- [`docs/proposta_llm.pdf`](docs/proposta_llm.pdf) — proposta técnica de uso
  de LLM (triagem de logs de execução), com pseudocódigo do ciclo completo.




