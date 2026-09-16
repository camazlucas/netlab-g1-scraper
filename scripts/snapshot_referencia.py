"""Snapshot da API dos 30 primeiros resultados (from=0/10/20).

Salva a resposta bruta com o horário da coleta, para explicar eventuais
divergências entre a amostra manual e o scraper corrigido.
"""

import json
from datetime import datetime
from pathlib import Path

import requests

URL_API = "https://busca.globo.com/v1/search"
CABECALHOS = {
    "x-tenant-id": "g1",
    "origin": "https://g1.globo.com",
    "x-track-urls": "true",
}
SAIDA = Path("data/reference")


def montar_corpo(inicio: int, tamanho: int = 10) -> list[dict]:
    return [
        {
            "search_profile": "sp_g1_globo_com",
            "query": "g1.info_query_recency",
            "params": {"q": "lgpd", "from": inicio, "size": tamanho},
        }
    ]


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    for inicio in (0, 10, 20):
        corpo = montar_corpo(inicio)
        coletado_em = datetime.now().astimezone().isoformat(timespec="seconds")
        resposta = requests.post(
            URL_API, json=corpo, headers=CABECALHOS, timeout=30
        )
        resposta.raise_for_status()
        dados = resposta.json()

        hits = dados[0]["result"]["hits"].get("hits", [])
        anuncios = sum("pubeditorial" in h["_source"] for h in hits)

        arquivo = SAIDA / f"snapshot_from_{inicio}.json"
        conteudo = {
            "coletado_em": coletado_em,
            "status_http": resposta.status_code,
            "corpo_requisicao": corpo,
            "resposta": dados,
        }
        arquivo.write_text(
            json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"from={inicio}: {len(hits)} hits, {anuncios} anúncios -> {arquivo}")


if __name__ == "__main__":
    main()