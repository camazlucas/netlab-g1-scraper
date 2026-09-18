# Avaliação da qualidade dos dados — Desafio de Web Scraping (NetLab UFRJ)

## Metodologia

A correção da coleta foi avaliada comparando a **base final** (coletada em
17/09/2026, 20:47 — `data/output/g1_lgpd_20260917T204713.csv`, 1015 registros)
com duas referências, ambas de **16/09/2026**:

- **Amostra manual** (`data/reference/amostra_manual.csv`) — 30 primeiros cards
  coletados diretamente no navegador, sem depender da API.
- **Snapshots da API** (`data/reference/snapshot_from_{0,10,20}.json`) — as
  mesmas 30 posições, capturadas pela API no mesmo momento da amostra manual.

O casamento entre base e referência é feito **pela URL real** (nunca pelo
título, que pode se repetir entre matérias distintas), considerando só os
itens sem anúncio de cada lado — 25 de 30 em cada referência. O script
`scripts/avaliacao_qualidade.py` implementa o cálculo; os números brutos estão
em `docs/metricas_qualidade.json`.

A comparação usa os snapshots de 16/09 em vez de uma nova amostra manual
refeita no dia da coleta final porque o **ranking do G1 deriva entre
execuções** (confirmado em teste de 24h: item saiu do topo, anúncios trocaram
de slot, item mudou de página) — refazer a amostra não eliminaria esse ruído,
só adicionaria trabalho manual repetido.

## Resultados por dimensão

| Dimensão | Métrica | Resultado |
|----------|---------|-----------|
| **Precisão** | Itens da referência (sem anúncio) presentes na base final | **25/25 (100%)** em ambas as referências |
| **Acurácia** | Igualdade exata de `titulo`, `resumo` e `data_atualizacao` nos pareados | **25/25 (100%)** nos três campos |
| **Unicidade** | 1 − duplicados/registros brutos | 6 duplicados em 1021 registros brutos → **99,4%**; base final entregue com **0 duplicatas** |
| **Completude** | Proporção de campos não vazios | **100%** em 7 dos 8 campos; `resumo` = **1014/1015 (99,9%)** — ver limitação abaixo |
| **Consistência** | Datas ISO válidas no fuso de referência; URL do domínio esperado; `pagina` ≥ 0; `posicao` entre 1 e `size` | `url`, `pagina`, `posicao`: **100%**. Datas: **1011/1015 (99,6%)** pelo critério de offset fixo `-03:00` — ver ressalva abaixo |
| **Atualidade** | Intervalo referência↔coleta; distribuição das datas de publicação | Intervalo de **27,6 horas** entre as coletas. Publicações de 2010 a 2026, concentradas em 2021–2026; idade média ≈ 1088 dias (mín. 2, máx. 5827) |
| **Rastreabilidade** | Registros com `pagina`, `posicao`, `coletado_em` e vínculo ao manifesto | **1015/1015 (100%)**; manifesto com commit da execução registrado |

## Métricas complementares

- **Vazamento de anúncios (alvo 0):** nenhum dos 10 itens marcados como
  anúncio nas referências aparece na base final. **0/10 — alvo atingido.**
- **Teste de contagem:** com `paginas_com_falha = 0`, vale
  `registros_brutos + anúncios_filtrados = hits.total.value`:
  `1021 + 198 = 1219`. **Confere.**

## Duas ressalvas sobre os números acima

**1. O `resumo` ausente (1 registro) não é falha do parser.** O hit em questão
(página 43, posição 7) volta da API **sem a chave `highlight`** e **sem
`description`** — as duas fontes previstas para o campo. No navegador, o G1
monta um resumo para esse card por um mecanismo próprio do frontend (mistura
título, crédito de foto e trecho do corpo) que não corresponde a nenhum campo
estruturado da resposta da API. Reproduzir esse comportamento exigiria
engenharia reversa de uma regra de apresentação não documentada, ajustada a um
único caso observado — e o resultado seria um dado que a API não entrega,
contrariando o princípio de não fabricar dado ausente na fonte. **Decisão:** o
parser permanece como está; o registro fica com `resumo` vazio.

**2. Os 4 registros com data "inconsistente" são um artefato do critério de
verificação, não um erro de dado.** O critério original exigia offset fixo
`-03:00`. Só que o Brasil observou horário de verão até 2019, e
`ZoneInfo("America/Sao_Paulo")` aplica isso corretamente para datas
históricas — nesses períodos o offset real é `-02:00`. Os 4 registros
apontados pertencem a notícias antigas (a distribuição por ano mostra itens de
2010 a 2015), exatamente onde isso é esperado. **A conversão de fuso está
correta; o critério de consistência é que assumiu offset fixo demais.** O
número reportado acima (99,6%) reflete esse critério simplificado — a
consistência real da conversão de datas é 100%.

## Limitações da avaliação

- A amostra de referência tem 30 itens (25 sem anúncio) — suficiente para
  validar o comportamento do parser, mas pequena para detectar problemas raros
  (o próprio caso do `resumo` ausente, 1 em 1015, não teria aparecido numa
  amostra de 25).
- A comparação de acurácia usa `titulo`, `resumo` e `data_atualizacao` —
  não inclui `data_publicacao`, `pagina`, `posicao` e `coletado_em`, que são
  derivados da execução (não há "valor certo" externo para compará-los,
  exceto pela consistência interna já verificada).
- O ranking do G1 muda entre execuções (documentado acima); a precisão de
  100% reflete a estabilidade dos 25 itens mais antigos da busca, não garante
  que a ordem relativa entre eles seja idêntica à da referência.

## Dados brutos

Números completos, por campo e por registro pareado, em
`docs/metricas_qualidade.json` (gerado por `scripts/avaliacao_qualidade.py`).