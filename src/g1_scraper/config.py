"""Configuração da coleta: endpoint, consulta, cabeçalhos e parâmetros de execução."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]

# --- Contrato da API (fixo; muda só se o site mudar) ---
ENDPOINT = "https://busca.globo.com/v1/search"
SEARCH_PROFILE = "sp_g1_globo_com"
QUERY = "g1.info_query_recency"
TETO_FROM = 10_000  # a API responde 400 quando `from + size` ultrapassa esse valor

CABECALHOS: dict[str, str] = {
    "x-tenant-id": "g1",
    "origin": "https://g1.globo.com",
    "x-track-urls": "1",
    "user-agent": "netlab-g1-scraper/1.0 (+https://github.com/camazlucas/netlab-g1-scraper)",
}


# --- Parâmetros da execução (ajustáveis pela CLI) ---
@dataclass(frozen=True, slots=True)
class Config:
    """Parâmetros de uma execução da coleta."""

    termo: str = "lgpd"
    size: int = 10
    max_paginas: int = 200
    timeout: tuple[float, float] = (5.0, 30.0)
    pausa: float = 1.5
    tentativas: int = 3
    backoff: float = 2.0
    fuso: str = "America/Sao_Paulo"
    dir_saida: Path = RAIZ / "data" / "output"


def corpo_consulta(termo: str, inicio: int, size: int) -> list[dict[str, Any]]:
    """Monta o corpo JSON da requisição de busca (uma lista com uma consulta)."""
    return [
        {
            "search_profile": SEARCH_PROFILE,
            "query": QUERY,
            "params": {"q": termo, "from": inicio, "size": size},
        }
    ]
