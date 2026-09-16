"""Etapa 4, questão 1: `from` avança de 10 em 10? Há sobreposição entre páginas?"""
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

API = "https://busca.globo.com/v1/search"
HEADERS = {"x-tenant-id": "g1", "origin": "https://g1.globo.com", "x-track-urls": "true"}
SAIDA = Path("data/baseline/api")


def buscar(inicio, tamanho=10):
    corpo = [{
        "search_profile": "sp_g1_globo_com",
        "query": "g1.info_query_recency",
        "params": {"q": "lgpd", "from": inicio, "size": tamanho},
    }]
    resp = requests.post(API, json=corpo, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


def url_real(url):
    return parse_qs(urlparse(url).query).get("u", [url])[0]


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    paginas = {}
    for inicio in (0, 10, 20):
        dados = buscar(inicio)
        (SAIDA / f"paginacao_from_{inicio}.json").write_text(
            json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        hits = dados[0]["result"]["hits"]
        urls = [url_real(h["_source"]["url"]) for h in hits["hits"]]
        paginas[inicio] = urls
        print(f"from={inicio}: {len(urls)} hits, total={hits['total']}, "
              f"únicas na página={len(set(urls))}")

    inicios = list(paginas)
    for i, a in enumerate(inicios):
        for b in inicios[i + 1:]:
            comuns = set(paginas[a]) & set(paginas[b])
            print(f"sobreposição from={a} x from={b}: {len(comuns)}")


if __name__ == "__main__":
    main()