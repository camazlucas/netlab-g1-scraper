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

(etapa 3: estrutura atual, HTML do requests vs. DOM do navegador)

## 8. Paginação

(etapa 4)
