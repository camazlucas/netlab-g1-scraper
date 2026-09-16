"""Etapa 3 (S1): verifica a extração da URL real (parâmetro u=) nos hits salvos."""
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ARQUIVO = Path("data/baseline/api/search_from_0.json")

dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
for i, hit in enumerate(dados[0]["result"]["hits"]["hits"]):
    fonte = hit["_source"]
    u = parse_qs(urlparse(fonte["url"]).query).get("u")
    real = u[0] if u else None
    anuncio = "pubeditorial" in fonte
    print(f"{i} anuncio={anuncio!s:5} issued={fonte.get('issued')} url={real}")