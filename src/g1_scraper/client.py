"""Cliente HTTP da API de busca: timeout, verificação de status e novas tentativas."""

import logging
import time
from typing import Any

import requests

from g1_scraper.config import CABECALHOS, ENDPOINT, Config, corpo_consulta

logger = logging.getLogger(__name__)

# Erros transitórios: vale repetir. Os demais (400, 403, 404) são definitivos.
STATUS_RETENTAVEIS = frozenset({429, 500, 502, 503, 504})


def criar_sessao() -> requests.Session:
    """Cria a sessão HTTP com os cabeçalhos exigidos pela API."""
    sessao = requests.Session()
    sessao.headers.update(CABECALHOS)
    return sessao


def buscar_pagina(sessao: requests.Session, config: Config, inicio: int) -> dict[str, Any] | None:
    """Requisita uma página de resultados.

    Devolve o JSON da resposta ou `None` se a requisição falhar em definitivo.
    Nenhuma falha de rede ou de status propaga para o chamador.
    """
    corpo = corpo_consulta(config.termo, inicio, config.size)

    for tentativa in range(1, config.tentativas + 1):
        try:
            resposta = sessao.post(ENDPOINT, json=corpo, timeout=config.timeout)
            resposta.raise_for_status()
            return resposta.json()

        except requests.HTTPError as erro:
            status = erro.response.status_code
            if status not in STATUS_RETENTAVEIS:
                logger.error("from=%d: HTTP %d, sem nova tentativa", inicio, status)
                return None
            logger.warning(
                "from=%d: HTTP %d (tentativa %d/%d)",
                inicio,
                status,
                tentativa,
                config.tentativas,
            )

        except (requests.Timeout, requests.ConnectionError) as erro:
            logger.warning(
                "from=%d: %s (tentativa %d/%d)",
                inicio,
                type(erro).__name__,
                tentativa,
                config.tentativas,
            )

        except ValueError:
            logger.error("from=%d: resposta não é JSON válido", inicio)
            return None

        except requests.RequestException as erro:
            logger.error("from=%d: falha inesperada (%s)", inicio, type(erro).__name__)
            return None

        if tentativa < config.tentativas:
            espera = config.backoff**tentativa
            logger.info("from=%d: aguardando %.1fs antes de repetir", inicio, espera)
            time.sleep(espera)

    logger.error("from=%d: esgotadas %d tentativas", inicio, config.tentativas)
    return None
