"""Etapa 3 (S1): confirma o conjunto mínimo e procura a URL real no _source."""
import requests

URL = "https://busca.globo.com/v1/search"
CORPO = [
    {"search_profile": "sp_g1_globo_com", "query": "g1.info_query_recency",
     "params": {"q": "lgpd", "from": 0, "size": 10}},
]
MINIMO = {
    "x-tenant-id": "g1",
    "origin": "https://g1.globo.com",
    "x-track-urls": "true",
}

r = requests.post(URL, json=CORPO, headers=MINIMO, timeout=15)
print(f"minimo status={r.status_code}")

if r.ok:
    fonte = r.json()[0]["result"]["hits"]["hits"][0]["_source"]
    print("campos do _source:", sorted(fonte))
    for chave, valor in fonte.items():
        if isinstance(valor, str) and "g1.globo.com" in valor:
            print(f"  {chave}: {valor[:100]}")