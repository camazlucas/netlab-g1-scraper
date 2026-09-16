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

## 6. Revisão do código original

Esta primeira versão do diagnóstico documenta apenas os problemas que serão corrigidos
nesta etapa. Os demais pontos levantados na revisão seguem em avaliação e podem ser
incluídos em versões posteriores.

| # | Problema | Efeito | Correção |
|---|----------|--------|----------|
| B1 | `resultados = dados_pagina` sobrescreve a lista a cada página | Só a última página seria salva | `resultados.extend(dados_pagina)` |
| B4 | `executar()` chamado no nível do módulo | Importar o arquivo dispara a coleta; o pytest faria requisições reais | `if __name__ == "__main__":` (será resolvido na modularização) |
| B5 | Requisição, parsing e gravação na mesma função | Não é possível testar a extração com HTML salvo | Separar rede, extração e gravação em funções distintas (será resolvido na modularização) |
| M2 | CSV aberto sem `encoding` e `newline` | No Windows, usa cp1252 (falha com caracteres fora da tabela, como emoji) e gera linhas em branco entre registros. Só se manifesta quando houver dados a gravar | `open(caminho, "w", encoding="utf-8", newline="")` |

**Observação:** essas correções não resolvem o CSV vazio. A causa do resultado vazio
será investigada na seção 7.

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

(etapa 4)
