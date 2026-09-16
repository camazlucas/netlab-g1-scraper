# Diagnóstico

## 1. Ambiente do baseline

| Item | Valor |
|---|---|
| Data/hora (UTC) | |
| Sistema operacional | |
| Python | |
| requests / beautifulsoup4 | |
| Commit | |

## 2. Execução do código original

Comando:

```bash
cd data/baseline
poetry run python ../../legacy/scraper_original.py
```

Saída do console:

```text
(colar aqui)
```

Exceções levantadas: (nenhuma / descrever)

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

``titulo,resumo,data_publicacao,url,pagina,coletado_em``



## 5. Observações iniciais

- Todas as páginas retornam HTTP 200, sem redirecionamento.
- O HTML tem o mesmo tamanho (57992 bytes) em page=0..4: o parâmetro `page` não altera a resposta.
- O termo "lgpd" não aparece no HTML recebido: hipótese de resultados renderizados via JavaScript (verificar na etapa 3).
- Nenhum `div.resultado` encontrado; CSV gerado vazio (só cabeçalho).

## 6. Revisão do código original

### 6.1 Bugs internos (falhariam mesmo com o site intacto)

| # | Problema | Efeito |
|---|----------|--------|
| B1 | `resultados = dados_pagina` sobrescreve a lista a cada página | Só a última página seria salva (correto: `extend`) |
| B2 | Sem `timeout`, `try/except` nem `raise_for_status()` | Erros HTTP (403, 404, página de bloqueio) viram "0 resultados" sem aviso; a falha fica silenciosa |
| B3 | URL montada por concatenação | Termos com espaço ou acento quebram a busca (usar `params=`) |
| B4 | `executar()` no nível do módulo, sem `if __name__ == "__main__"` | Importar o módulo dispara a coleta; impede testes |
| B5 | Coleta, parsing e gravação na mesma função | Dificulta testar cada etapa isoladamente |

### 6.2 Problemas mascarados (só aparecem quando houver cards)

| # | Problema | Efeito esperado |
|---|----------|-----------------|
| M1 | `.find(...).get_text()` encadeado | `AttributeError` se um campo faltar em um card |
| M2 | CSV sem `encoding="utf-8"` e `newline=""` | No Windows: cp1252 (erro com emoji etc.) e linhas em branco |
| M3 | Sem `.strip()` nem deduplicação | Espaços extras e resultados repetidos entre páginas |
| M4 | `href` usado sem normalização | Links relativos ou de redirecionamento |
| M5 | `datetime.now()` sem fuso | Horário da coleta ambíguo |

### 6.3 Dependentes do site (a verificar)

| # | Ponto | Onde será verificado |
|---|-------|----------------------|
| S1 | Seletores `div.resultado`, `div.titulo`, `p.resumo`, `span.data` | Seção 7 |
| S2 | Ausência de User-Agent (hoje recebe HTTP 200, mas é um risco) | Seção 7 |
| S3 | `range(5)` começa em `page=0` e não coleta `page=5` | Seção 8 (base da paginação) |

**Conclusão parcial:** o CSV vazio não se explica só pelo código. Mesmo corrigindo B1–B5,
os seletores não encontram nada (0 `div.resultado`, "lgpd" ausente no HTML), o que aponta
para mudança no site. B2 explica por que a falha passou despercebida.

## 7. Mudanças no site

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

### 9.4 Métricas (calculadas após a correção)
Calculadas sobre os itens com `eh_anuncio = nao`, casando amostra e base pela URL.

| Métrica | Definição | Esperado |
|---|---|---|
| Cobertura | Fração das URLs da amostra presentes na base | 100% |
| Acurácia por campo | Percentual de acertos em `titulo`, `resumo` e `data_publicacao` após normalizar espaços | 100% |
| Vazamento de anúncios | Itens com `eh_anuncio = sim` presentes na base | 0 |
| Duplicatas | URLs repetidas na base | 0 |

Critérios de comparação:
- **Ordem:** não conta como erro, só é registrada, porque a relevância pondera recência.
- **Data:** comparação pelo dia no fuso `-03:00`. Datas relativas são convertidas a partir de `coletado_em`, com tolerância.
- **Resumo:** critério (igualdade exata ou tolerante) a definir na comparação, porque o site exibe trechos.
- **Contagem (teste automatizado):** itens na base + anúncios descartados + duplicatas descartadas = `hits.total.value`.
