# netlab-g1-scraper

Correção de uma rotina de web scraping que coleta os resultados da busca por
"lgpd" no G1. Desafio do processo seletivo do NetLab UFRJ.

> Em construção. Diagnóstico em [`docs/diagnostico.md`](docs/diagnostico.md).

## Instalação

Com Poetry:

```bash
poetry install
```

Alternativa com pip:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Baseline (código original)

```bash
cd data/baseline
poetry run python ../../legacy/scraper_original.py
cd ../..
poetry run python scripts/baseline.py
```

## Testes

```bash
poetry run pytest
poetry run ruff check .
```
