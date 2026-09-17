"""Deduplicação de registros pela URL real da matéria."""

import logging
from urllib.parse import urlsplit, urlunsplit

from g1_scraper.models import Resultado

logger = logging.getLogger(__name__)


def chave(url: str | None) -> str | None:
    """Devolve a chave de deduplicação: a URL com esquema e domínio em minúsculas.

    Nenhuma outra normalização é aplicada — caminho, query e fragmento preservam
    a forma original, porque o site pode tratá-los como recursos distintos.
    """
    if not url:
        return None
    partes = urlsplit(url)
    return urlunsplit(
        (partes.scheme.lower(), partes.netloc.lower(), partes.path, partes.query, partes.fragment)
    )


def deduplicar(registros: list[Resultado]) -> tuple[list[Resultado], int, int]:
    """Remove registros com URL repetida, preservando a primeira ocorrência.

    Devolve os registros únicos, a quantidade de duplicados descartados e a
    quantidade de registros sem URL (mantidos na base, por não terem chave).
    """
    vistas: set[str] = set()
    unicos: list[Resultado] = []
    duplicados = 0
    sem_url = 0

    for registro in registros:
        identificador = chave(registro.url)
        if identificador is None:
            sem_url += 1
            unicos.append(registro)
            continue
        if identificador in vistas:
            duplicados += 1
            logger.debug("duplicado descartado: %s", identificador)
            continue
        vistas.add(identificador)
        unicos.append(registro)

    return unicos, duplicados, sem_url
