"""Etapa 3 (S2): compara a resposta com o UA padrão e com UA de navegador."""
from pathlib import Path

import requests

URL = "https://g1.globo.com/busca/?q=lgpd&page=0"
UA_NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
SAIDA = Path("data/baseline/html")

for nome, headers in [("ua_padrao", {}), ("ua_navegador", {"User-Agent": UA_NAVEGADOR})]:
    r = requests.get(URL, headers=headers, timeout=15)
    (SAIDA / f"page_0_{nome}.html").write_bytes(r.content)
    print(
        f"{nome}: status={r.status_code} bytes={len(r.content)} "
        f"lgpd={r.text.lower().count('lgpd')} url_final={r.url}\n"
        f"  UA enviado: {r.request.headers['User-Agent']}"
    )