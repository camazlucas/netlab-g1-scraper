"""Etapa 4, questão 2: comportamento no fim dos resultados e limite de `from`."""
import json
from pathlib import Path

import requests
from inspecao_paginacao import buscar

SAIDA = Path("data/baseline/api")


def main():
    for inicio in (1200, 1210, 1215, 1219, 1220, 5000, 9990, 10000):
        try:
            dados = buscar(inicio)
        except requests.HTTPError as erro:
            resp = erro.response
            print(f"from={inicio}: HTTP {resp.status_code} -> {resp.text[:200]!r}")
            continue
        (SAIDA / f"paginacao_from_{inicio}.json").write_text(
            json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        hits = dados[0]["result"]["hits"]
        try:
            hits = dados[0]["result"]["hits"]
            print(f"from={inicio}: HTTP 200, {len(hits['hits'])} hits, total={hits['total']}")
        except (KeyError, IndexError, TypeError):
            print(f"from={inicio}: HTTP 200, formato diferente -> "
                  f"{json.dumps(dados, ensure_ascii=False)[:300]}")

if __name__ == "__main__":
    main()