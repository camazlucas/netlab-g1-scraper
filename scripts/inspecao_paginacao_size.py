"""Etapa 4, questão 3: `size` aceita valores maiores que 10?"""
import json
from pathlib import Path

import requests
from inspecao_paginacao import buscar, url_real

SAIDA = Path("data/baseline/api")


def urls(dados):
    hits = dados[0]["result"]["hits"].get("hits", [])
    return [url_real(h["_source"]["url"]) for h in hits]


def main():
    for tamanho in (20, 50, 100, 500):
        try:
            dados = buscar(0, tamanho)
        except requests.HTTPError as erro:
            resp = erro.response
            print(f"size={tamanho}: HTTP {resp.status_code} -> {resp.text[:200]!r}")
            continue
        (SAIDA / f"paginacao_size_{tamanho}.json").write_text(
            json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"size={tamanho}: HTTP 200, {len(urls(dados))} hits")

    juntas = urls(buscar(0)) + urls(buscar(10))
    size_20 = urls(buscar(0, 20))
    print(f"size=20 igual a from=0 + from=10 (mesma ordem): {size_20 == juntas}")
    print(f"size=20 igual a from=0 + from=10 (mesmo conjunto): {set(size_20) == set(juntas)}")


if __name__ == "__main__":
    main()