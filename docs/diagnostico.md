# Diagnóstico

## 1. Ambiente do baseline

| Item | Valor |
|---|---|
| Data/hora (UTC) | 2026-09-16T13:28:04+00:00 |
| Sistema operacional | Windows 11 |
| Python | 3.12 |
| requests / beautifulsoup4 | 2.34.2 / 4.15.0 |
| Commit | `d325dac` (chore: adiciona script de coleta de evidências do baseline) |

## 2. Execução do código original

Comando:

```bash
cd data/baseline
poetry run python ../../legacy/scraper_original.py
```

Saída do console:

```text
Coletando: https://g1.globo.com/busca/?q=lgpd&page=0
Coletando: https://g1.globo.com/busca/?q=lgpd&page=1
Coletando: https://g1.globo.com/busca/?q=lgpd&page=2
Coletando: https://g1.globo.com/busca/?q=lgpd&page=3
Coletando: https://g1.globo.com/busca/?q=lgpd&page=4
Coleta finalizada.
```

Exceções levantadas: nenhuma — a execução termina normalmente e imprime
"Coleta finalizada.", apesar do CSV sair vazio (só cabeçalho). É exatamente o
tipo de falha silenciosa que o diagnóstico investiga a seguir.

## 3. Evidências por página

Gerado por `scripts/baseline.py` (mesmas requisições do legado, sem headers).
Os HTMLs brutos ficam em `data/baseline/html/`.

### Baseline executado em 2026-09-16T13:28:04+00:00

| page | status | redirecionou | url_final | bytes | ocorrencias_termo | cards | com_titulo | com_resumo | com_data | com_link | erro |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 200 | False | https://g1.globo.com/busca/?q=lgpd&page=0 | 57992 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 1 | 200 | False | https://g1.globo.com/busca/?q=lgpd&page=1 | 57992 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 200 | False | https://g1.globo.com/busca/?q=lgpd&page=2 | 57992 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 200 | False | https://g1.globo.com/busca/?q=lgpd&page=3 | 57992 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 200 | False | https://g1.globo.com/busca/?q=lgpd&page=4 | 57992 | 0 | 0 | 0 | 0 | 0 | 0 |  |

#### CSV do legado (data\baseline\g1_lgpd.csv)

- Encoding usado na leitura: cp1252
- Linhas de dados: 0
- Páginas presentes: []
- `titulo` vazio: 0
- `resumo` vazio: 0
- `data_publicacao` vazio: 0
- `url` vazio: 0
- `pagina` vazio: 0
- `coletado_em` vazio: 0

## 4. CSV gerado pelo legado

`titulo,resumo,data_publicacao,url,pagina,coletado_em`



## 5. Observações iniciais

- Todas as páginas retornam HTTP 200, sem redirecionamento.
- O HTML tem o mesmo tamanho (57992 bytes) em page=0..4: o parâmetro `page` não altera a resposta.
- O termo "lgpd" não aparece no HTML recebido: hipótese de resultados renderizados via JavaScript (verificar na etapa 3).
- Nenhum `div.resultado` encontrado; CSV gerado vazio (só cabeçalho).

## 6. Revisão do código original

Esta seção lista os problemas identificados na leitura do código original
(`legacy/scraper_original.py`), sem executá-lo. Os identificadores atribuídos aqui
(B, M, S) são usados no restante do documento e nas mensagens de commit.

> **Nota de revisão (etapa 6).** As tabelas abaixo foram escritas na etapa 2, antes de
> a origem dos dados ser conhecida. O inventário de problemas permanece o mesmo — ele
> descreve o código original, que não mudou —, mas a **coluna de status foi
> reclassificada** após as seções 7 a 9, por dois motivos:
>
> 1. A descoberta de que os resultados vêm da API `busca.globo.com/v1/search`
>    (seção 7) tornou alguns itens obsoletos: eles descrevem problemas de um caminho
>    de coleta que deixou de existir.
> 2. Durante a etapa 2 vigorou uma restrição de escopo deliberada: corrigir apenas
>    B1, B4, B5 e M2, para não alterar o comportamento do código enquanto o
>    diagnóstico estava em andamento. Essa restrição valia para a **fase de
>    diagnóstico**, não para a entrega. Os demais itens foram então marcados como
>    "adiados", rótulo que não indicava destino. A revisão substitui esse rótulo por
>    uma classificação com destino explícito.
>
> Os itens B6 a B9, M6 e M7 receberam identificador nesta revisão; na versão anterior
> apareciam sem numeração no texto corrido.

### 6.1 Legenda de status

| Status | Significado |
|--------|-------------|
| **Obrigatório** | Exigido explicitamente pelo enunciado do desafio. Corrigido na etapa indicada. |
| **Obsoleto** | A mudança da fonte de dados (HTML → API) eliminou o problema. Mantido no registro como histórico. |
| **Descartado** | Hipótese verificada e afastada, com a evidência registrada na seção indicada. |
| **Limitação** | Fica fora do escopo desta entrega e é documentado no README. |

### 6.2 Bugs internos (falhariam mesmo com o site intacto)

| # | Problema | Efeito | Status |
|---|----------|--------|--------|
| B1 | `resultados = dados_pagina` sobrescreve a lista a cada página | Só a última página seria salva (correto: `extend`) | Obrigatório — etapa 6 |
| B2 | Sem `timeout`, `try/except` nem `raise_for_status()` | Erros HTTP (403, 404, página de bloqueio) viram "0 resultados" sem aviso; a falha fica silenciosa | Obrigatório — etapa 6 |
| B3 | URL montada por concatenação, sem *URL encoding* | Termos com espaço ou acento quebrariam a busca (correto: `params=`) | Obsoleto — a consulta agora vai no corpo JSON do POST |
| B4 | `executar()` no nível do módulo, sem `if __name__ == "__main__"` | Importar o módulo dispara a coleta; impede testes | Obrigatório — etapa 6 |
| B5 | Coleta, parsing e gravação na mesma função | Dificulta testar cada etapa isoladamente | Obrigatório — etapa 6 |
| B6 | `TOTAL_PAGINAS` fixo, sem condição de parada derivada da resposta | Coleta páginas inexistentes ou interrompe antes do fim dos resultados | Obrigatório — etapa 6 |
| B7 | `print` como único mecanismo de log, sem nível nem horário; mensagem final ("Coleta finalizada.") exibida mesmo com zero registros | Impede acompanhar e diagnosticar a execução; mascara o resultado vazio | Obrigatório — etapa 6 |
| B8 | `sleep(0.2)` fixo e muito curto para um portal de grande porte | Risco de sobrecarga e de bloqueio | Obrigatório — etapa 6 |
| B9 | Nomes dos campos duplicados entre o dicionário do registro e `fieldnames` | Alterar um exige lembrar do outro; fonte de inconsistência | Obrigatório — etapa 6 (`dataclass` como fonte única) |

### 6.3 Problemas mascarados (só apareceriam quando houvesse resultados)

Na execução original o laço nunca chegou a rodar, porque nenhum card foi encontrado.
Estes problemas, portanto, não produziram sintoma — mas produziriam assim que a coleta
voltasse a funcionar. A mudança para a API altera a **forma** de vários deles, não a
sua existência.

| # | Problema (no código original) | Forma correspondente na coleta via API | Status |
|---|-------------------------------|----------------------------------------|--------|
| M1 | `.find(...).get_text()` encadeado lança `AttributeError` se um campo faltar | Chaves ausentes no `_source` de um hit (nem todo hit traz `summaryBlocks`, `issued` etc.) | Obrigatório — etapa 6 |
| M2 | CSV sem `encoding="utf-8"` e `newline=""` | Inalterado | Obrigatório — etapa 6 |
| M3 | Sem `.strip()` nos textos e sem deduplicação | `strip` segue necessário; a deduplicação passa a usar a **URL real**, conforme decidido na seção 9 | Obrigatório — etapa 6 |
| M4 | `href` usado sem normalização (link relativo, de redirecionamento, e `find("a")` pega o primeiro link do card) | O campo `url` do `_source` é link de rastreamento; a URL real está no parâmetro `u=` e precisa ser decodificada | Obrigatório — etapa 6 (deixou de ser opcional: sem isso não há URL real nem chave de deduplicação) |
| M5 | `datetime.now()` sem fuso horário no campo `coletado_em` | Inalterado | Obrigatório — etapa 6 |
| M6 | Data de publicação gravada como texto bruto, sem normalização | `issued` vem em ISO, mas com fusos mistos (`Z` e `-03:00`), exigindo normalização para comparação e ordenação | Obrigatório — etapa 6 |
| M7 | Arquivo de saída com nome fixo, sobrescrevendo coletas anteriores | Inalterado | Obrigatório — etapa 6 (nome com timestamp) |

### 6.4 Dependentes do site

| # | Ponto | Verificação | Status |
|---|-------|-------------|--------|
| S1 | Seletores `div.resultado`, `div.titulo`, `p.resumo`, `span.data` não encontram nada | Confirmado na seção 7: os resultados são inseridos via JavaScript e não existem no HTML recebido pelo `requests` | Obsoleto — o caminho HTML foi substituído pela coleta via API |
| S2 | Ausência de User-Agent de navegador | Testado na seção 7: UA padrão e UA de navegador produzem resposta idêntica | Descartado |
| S3 | `range(5)` começa em `page=0` e nunca coleta `page=5` | Ver correção de registro abaixo | Descartado |

**Correção de registro — S3.** Na etapa 3, S3 foi descartada com a justificativa de que
"a paginação do G1 começa em `page=0`". A seção 8 mostrou que essa justificativa está
errada: o parâmetro `page=N` da URL é **ignorado** pelo site — em `page=0`, `page=1` e
`page=2` a página envia sempre `from=0` à API. A paginação real ocorre por rolagem
infinita e pelo botão "Ver mais", que incrementam `from` de 10 em 10. A conclusão
(S3 não é a causa do CSV vazio) se mantém, mas pelo motivo correto.

### 6.5 Pontos positivos do código original

Registrados para leitura equilibrada do legado:

- imports separados entre biblioteca padrão e externas, conforme a PEP 8;
- constantes de configuração isoladas no topo do arquivo;
- uso de `with open(...)`, garantindo o fechamento do arquivo;
- `csv.DictWriter` com `fieldnames` explícito, fixando a ordem das colunas;
- campos `pagina` e `coletado_em` já presentes, cobrindo parte da rastreabilidade
  exigida pelo desafio;
- pausa entre requisições já prevista, ainda que curta demais (B8).

### 6.6 Escopo consolidado da correção

| Destino | Itens |
|---------|-------|
| Etapa 6 (implementação) | B1, B2, B4, B5, B6, B7, B8, B9, M1, M2, M3, M4, M5, M6, M7 |
| Obsoletos (registro histórico) | B3, S1 |
| Descartados (hipóteses afastadas) | S2, S3 |
| Limitações (README, etapa 10) | Uso de API não documentada publicamente; ausência do Beautiful Soup no caminho principal de coleta; exclusão de anúncios da base; teto `from + size ≤ 10000`; variação de `max_score` entre execuções |

### 6.7 Conclusão parcial

O CSV vazio não se explica pelo código sozinho. Mesmo corrigindo B1 a B9 e M1 a M7, os
seletores não encontrariam nada: o HTML recebido não contém a palavra "lgpd" nem um
único `div.resultado`. A causa está em mudança no site (S1), detalhada na seção 7; B2 e
B7 explicam por que a falha passou despercebida, ao transformar a ausência de resultados
em uma execução aparentemente bem-sucedida.

## 7. Estrutura atual da página

### 7.1 Hipótese S2 – User-Agent
Requisição a `?q=lgpd&page=0` com o UA padrão (`python-requests/2.34.2`) e com UA de
navegador: ambas status 200, 57992 bytes e 0 ocorrências de "lgpd" (contagem sem
diferenciar maiúsculas). **Descartada**: o servidor não altera a resposta pelo UA.
Evidência: `data/baseline/html/page_0_ua_padrao.html` e `page_0_ua_navegador.html`.

### 7.2 Hipótese S1 – Conteúdo carregado via JavaScript
- Código-fonte (Ctrl+U): 0 ocorrências de "lgpd".
- DOM renderizado (DevTools): 37 ocorrências (não equivalem a 37 resultados; cada card
  repete o termo nos links e no resumo).
- Os cards atuais são `li.widget--card` (`id="search-result-item-N"`); não existe
  `div.resultado`.

**Confirmada**: o HTML entregue pelo servidor é apenas a estrutura da página; os
resultados são inseridos no DOM por JavaScript. Por isso o código original, que faz
parsing do HTML bruto, retorna 0 resultados sem lançar exceção.

### 7.3 Origem dos dados
- Endpoint: `POST https://busca.globo.com/v1/search`, resposta em JSON.
- O corpo agrupa 4 consultas; a lista principal é `g1.info_query_recency`
  (`size=10`). As demais (`navigational_query`, `live_query`, `pub_editorial_query`,
  `size=1`) alimentam blocos auxiliares.
- O navegador dispara a mesma requisição duas vezes, com corpo idêntico.
- A API responde fora do navegador, sem cookies. Cabeçalhos testados removendo um
  por vez:

| Cabeçalho | Necessário |
|---|---|
| `x-tenant-id: g1` | sim |
| `origin: https://g1.globo.com` | sim |
| `x-track-urls` | sim (só a presença; `false` não altera o retorno) |
| `referer` | não |
| `x-must-thumborize` | não |

Evidência: `data/baseline/api/search_from_0.json`.

### 7.4 Campos disponíveis no `_source`
`title`, `url`, `issued`, `modified`, `caption`, `body`, `section`, `pubeditorial`,
entre outros. `total` = 1219 resultados para "lgpd".

### 7.5 Pontos de atenção para a correção
- **URL (reabre M4):** `url` é um link de rastreamento (`measures.globo.com`); a URL
  real está codificada no parâmetro `u=` e foi extraída com sucesso nos 10 hits.
- **Data (liga-se a M5):** `issued` é ISO 8601, mas com fusos mistos (`Z` e `-03:00`).
- **Anúncios:** 3 dos 10 primeiros hits têm `pubeditorial` (Especial Publicitário).
- **Relevância e ordem:** vários títulos não citam LGPD, e a ordem não é estritamente
  cronológica.

## 8. Paginação

### 8.1 Relação entre `page=N` e a API
- O site ignora o parâmetro `page` da URL: em `page=0`, `1` e `2` a requisição
  `POST v1/search` envia `from=0, size=10` (verificado no DevTools).
- A paginação real acontece pelo botão "Ver mais", que envia uma nova requisição
  com `from` incrementado de 10 e `size=10`, contendo apenas a consulta
  `g1.info_query_recency` (sem os blocos auxiliares).
- Isso explica, junto com a S1, por que o laço `page=0..4` do código original
  obtinha sempre o mesmo HTML (etapa 1).

### 8.2 Incremento e sobreposição (`scripts/inspecao_paginacao.py`)
- `from=0`, `10` e `20` retornam 10 hits cada, sem sobreposição de URLs reais.
- A API aceita o corpo apenas com a consulta principal.

### 8.3 Fim dos resultados e limite (`scripts/inspecao_paginacao_fim.py`)
- `from=1210` retorna 9 hits; `from=1215` retorna 4 (total = 1219).
- A partir de `from=1219`: HTTP 200, mas a chave `hits.hits` não existe
  (não é uma lista vazia).
- `from=9990` responde normalmente; `from=10000` retorna HTTP 400 com corpo `{}`.
  Hipótese: limite `from + size ≤ 10000` do Elasticsearch. Não afeta a coleta
  de "lgpd" (1219 resultados).

### 8.4 Tamanho da página (`scripts/inspecao_paginacao_size.py`)
- `size=20`, `50`, `100` e `500` retornam a quantidade pedida.
- `size=20` é idêntico a `from=0` + `from=10`, na mesma ordem.
- Decisão: manter `size=10`, igual ao site, para reduzir a carga no servidor.

### 8.5 Estabilidade (`scripts/inspecao_paginacao_estabilidade.py`)
- 5 repetições de `from=0, size=50`: mesmo `total`, mesma ordem e mesmo conjunto;
  os 10 primeiros coincidem com a coleta da questão 1, feita minutos antes.
- O `max_score` varia entre execuções mais espaçadas (≈20784 → 20710).
  Hipótese: o perfil `info_query_recency` pondera recência.

### 8.6 Consequências para o scraper
- Paginar pela API com `from` de 10 em 10, e não pela URL `page=N`.
- Parar quando `hits.get("hits", [])` estiver vazio ou `from >= total`,
  sem depender de erro HTTP.
- Limitação: se notícias novas forem publicadas durante a coleta, resultados
  podem se deslocar entre páginas (duplicatas ou lacunas). Mitigação: coleta em
  execução única e deduplicação pela URL real.

- O arquivo `paginacao_size_500.json` (3,7 MB) não é versionado; pode ser
  regenerado com o script.

Evidências: `data/baseline/api/paginacao_*.json` e `estabilidade_rep_*.json`.

## 9. Amostra de referência (etapa 5)

### 9.1 Objetivo
Montar um gabarito independente, antes da correção, para medir a qualidade da base gerada pelo scraper corrigido.

### 9.2 Coleta
- **Fonte:** página renderizada no navegador (janela anônima) em `https://g1.globo.com/busca/?q=lgpd`. A API não foi usada como fonte, para que a comparação não seja circular.
- **Extração:** texto dos cards via console (`innerText`). A URL real foi decodificada do parâmetro `u=` e conferida abrindo alguns cards, incluindo um vídeo.
- **Tamanho:** 30 primeiros cards (páginas 0, 1 e 2, equivalentes a `from` = 0, 10, 20).
- **Arquivo:** `data/reference/amostra_manual.csv` (UTF-8), com as colunas do CSV legado mais `posicao` e `eh_anuncio`. `data_publicacao` foi guardada como exibida, inclusive datas relativas ("há 1 dia").
- **Snapshot:** logo após a coleta, `scripts/snapshot_referencia.py` salvou as respostas da API em `data/reference/snapshot_from_{0,10,20}.json`, com o horário da coleta.
- **Fim dos resultados:** não entra na amostra manual (exigiria cerca de 121 carregamentos). É coberto por teste automatizado de contagem (seção 9.4).

### 9.3 Observações
- **Carregamento:** os primeiros carregamentos são disparados por rolagem infinita, e o botão "Ver mais" só aparece depois. Cada carregamento continua sendo `from` +10 com `size=10`, o que confirma a seção 8.
- **Cards de vídeo:** usam a classe `li.video-widget--card`, diferente de `li.widget--card`. A amostra tem 4 vídeos, todos em `g1.globo.com`.
- **Anúncios:** identificados pelo selo "Especial Publicitário". São 5 na amostra (3, 1 e 1 por página), a mesma contagem de hits com `pubeditorial` no snapshot.
- **Títulos semelhantes:** há itens com títulos quase iguais e URLs diferentes (ex.: vídeo e notícia sobre o vazamento de dados de pessoas com HIV na BA). A deduplicação deve usar a URL, não o título.
- **Resumo:** o card exibe trechos com o termo buscado, com reticências e trechos unidos por " — ".

### 9.4 Métricas — resultado final

Calculadas sobre os itens com `eh_anuncio = nao`, casando amostra e base pela
URL real. Metodologia completa, números por campo e as duas ressalvas sobre
os resultados estão em `docs/avaliacao_qualidade.md`
(`docs/metricas_qualidade.json` para os dados brutos).

| Métrica | Definição | Resultado |
|---|---|---|
| Cobertura | Fração das URLs da amostra presentes na base | 25/25 (100%) em ambas as referências |
| Acurácia por campo | Igualdade exata em `titulo`, `resumo` e `data_atualizacao` | 25/25 (100%) nos três campos |
| Vazamento de anúncios | Itens com `eh_anuncio = sim` presentes na base | 0/10 |
| Duplicatas | URLs repetidas na base final | 0 (6 descartadas de 1021 brutos) |

Critérios de comparação (fechados):
- **Ordem:** não conta como erro, só é registrada, porque a relevância pondera
  recência — confirmado na seção 8.5 (deriva de `max_score` entre execuções).
- **Data:** comparação pelo dia no fuso `-03:00`, contra `data_atualizacao`
  (não `data_publicacao` — é o campo que o card do G1 exibe). Datas relativas
  da amostra manual foram convertidas a partir de `coletado_em`, com
  tolerância.
- **Resumo:** igualdade exata — decisão fechada na etapa 6, já que reticências
  e a formatação de junção (`" — "`) passaram a ser tratadas como dado, não
  como apresentação (ver seção 6.3, M3).
- **Contagem (teste automatizado):** registros na base + anúncios filtrados =
  `hits.total.value`. Confirmado na coleta final: `1021 + 198 = 1219`.
