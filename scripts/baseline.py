"""Coleta de evidências do baseline (etapa 1).

Repete as mesmas requisições do código legado (sem headers, page=0..4) e
registra, por página, o que o scraper original "enxerga". Também analisa o
CSV gerado pelo legado. Não altera nada em legacy/.

Uso, a partir da raiz do repositório:
    poetry run python scripts/baseline.py
"""

from __future__ import annotations

import csv
import locale
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL_BASE = "https://g1.globo.com/busca/"
TERMO_BUSCA = "lgpd"
PAGINAS = range(5)  # mesmo intervalo do original: page=0..4
CAMPOS = ["titulo", "resumo", "data_publicacao", "url", "pagina", "coletado_em"]

RAIZ = Path(__file__).resolve().parents[1]
DIR_BASELINE = RAIZ / "data" / "baseline"
DIR_HTML = DIR_BASELINE / "html"
CSV_LEGADO = DIR_BASELINE / "g1_lgpd.csv"


def inspecionar_pagina(pagina: int) -> dict:
    linha: dict = {"page": pagina}
    try:
        resp = requests.get(
            URL_BASE, params={"q": TERMO_BUSCA, "page": pagina}, timeout=30
        )
    except requests.RequestException as exc:
        linha["erro"] = type(exc).__name__
        return linha

    (DIR_HTML / f"page_{pagina}.html").write_text(resp.text, encoding="utf-8")
    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.find_all("div", class_="resultado")
    linha.update(
        status=resp.status_code,
        redirecionou=bool(resp.history),
        url_final=resp.url,
        bytes=len(resp.content),
        ocorrencias_termo=resp.text.lower().count(TERMO_BUSCA),
        cards=len(cards),
        com_titulo=sum(c.find("div", class_="titulo") is not None for c in cards),
        com_resumo=sum(c.find("p", class_="resumo") is not None for c in cards),
        com_data=sum(c.find("span", class_="data") is not None for c in cards),
        com_link=sum(c.find("a") is not None for c in cards),
    )
    return linha


def imprimir_tabela(linhas: list[dict]) -> None:
    colunas = [
        "page", "status", "redirecionou", "url_final", "bytes",
        "ocorrencias_termo", "cards", "com_titulo", "com_resumo",
        "com_data", "com_link", "erro",
    ]
    print("| " + " | ".join(colunas) + " |")
    print("|" + "---|" * len(colunas))
    for linha in linhas:
        print("| " + " | ".join(str(linha.get(c, "")) for c in colunas) + " |")


def analisar_csv(caminho: Path) -> None:
    print(f"\n## CSV do legado ({caminho.relative_to(RAIZ)})\n")
    if not caminho.exists():
        print("Arquivo não encontrado. Rode o scraper legado antes (ver README).")
        return
    encoding = locale.getpreferredencoding(False)
    with caminho.open(encoding=encoding, newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))

    print(f"- Encoding usado na leitura: {encoding}")
    print(f"- Linhas de dados: {len(linhas)}")
    print(f"- Páginas presentes: {sorted({l.get('pagina') for l in linhas})}")
    for campo in CAMPOS:
        vazios = sum(not (l.get(campo) or "").strip() for l in linhas)
        print(f"- `{campo}` vazio: {vazios}")


def main() -> None:
    DIR_HTML.mkdir(parents=True, exist_ok=True)
    inicio = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"# Baseline executado em {inicio}\n")

    linhas = []
    for pagina in PAGINAS:
        linhas.append(inspecionar_pagina(pagina))
        time.sleep(1)

    imprimir_tabela(linhas)
    analisar_csv(CSV_LEGADO)


if __name__ == "__main__":
    main()
