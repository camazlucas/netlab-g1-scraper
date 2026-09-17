"""Orquestração da coleta: laço de paginação, acumulação e métricas da execução."""

import logging
import time
from dataclasses import fields
from typing import Any

import requests

from g1_scraper.client import buscar_pagina, criar_sessao
from g1_scraper.config import TETO_FROM, Config
from g1_scraper.dedup import deduplicar
from g1_scraper.models import Resultado
from g1_scraper.parser import extrair_hits, extrair_registros, extrair_total
from g1_scraper.storage import agora

logger = logging.getLogger(__name__)

FALHAS_CONSECUTIVAS_MAX = 3


def contar_campos_ausentes(registros: list[Resultado]) -> dict[str, int]:
    """Conta quantos registros têm cada campo vazio."""
    return {
        campo.name: sum(1 for r in registros if getattr(r, campo.name) is None)
        for campo in fields(Resultado)
    }


def coletar(
    config: Config, sessao: requests.Session | None = None
) -> tuple[list[Resultado], dict[str, Any]]:
    """Percorre as páginas da busca e devolve os registros únicos e as métricas.

    Nenhuma falha de rede interrompe a coleta: páginas que falham são contadas e
    a execução segue, preservando o que já foi coletado.
    """
    sessao = sessao or criar_sessao()
    coletados: list[Resultado] = []
    momento = agora(config.fuso)
    coletado_em = momento.isoformat()

    inicio = 0
    pagina = 0
    total_declarado: int | None = None
    paginas_ok = 0
    anuncios = 0
    falhas = 0
    falhas_seguidas = 0
    motivo = "limite de páginas atingido"

    while pagina < config.max_paginas:
        if inicio + config.size > TETO_FROM:
            motivo = f"teto da API alcançado (from={inicio})"
            break

        resposta = buscar_pagina(sessao, config, inicio)

        if resposta is None:
            falhas += 1
            falhas_seguidas += 1
            if falhas_seguidas >= FALHAS_CONSECUTIVAS_MAX:
                motivo = f"{falhas_seguidas} falhas consecutivas (from={inicio})"
                break
            inicio += config.size
            pagina += 1
            time.sleep(config.pausa)
            continue

        falhas_seguidas = 0

        if total_declarado is None:
            total_declarado = extrair_total(resposta)
            logger.info("total declarado pela API: %s", total_declarado)

        if not extrair_hits(resposta):
            motivo = f"resposta sem hits (from={inicio})"
            break

        registros, anuncios_pagina = extrair_registros(resposta, pagina, coletado_em, config.fuso)
        coletados.extend(registros)  # acumula, nunca sobrescreve
        anuncios += anuncios_pagina
        paginas_ok += 1
        logger.info(
            "página %d (from=%d): %d registros, %d anúncios | acumulado: %d",
            pagina,
            inicio,
            len(registros),
            anuncios_pagina,
            len(coletados),
        )

        inicio += config.size
        pagina += 1

        if total_declarado is not None and inicio >= total_declarado:
            motivo = f"fim do conjunto (from={inicio} >= total={total_declarado})"
            break

        time.sleep(config.pausa)

    unicos, duplicados, sem_url = deduplicar(coletados)

    metricas: dict[str, Any] = {
        "paginas_coletadas": paginas_ok,
        "paginas_com_falha": falhas,
        "total_declarado": total_declarado,
        "registros_brutos": len(coletados),
        "registros_na_base": len(unicos),
        "duplicados_descartados": duplicados,
        "anuncios_filtrados": anuncios,
        "registros_sem_url": sem_url,
        "campos_ausentes": contar_campos_ausentes(unicos),
        "motivo_parada": motivo,
    }
    logger.info("coleta encerrada: %s", motivo)
    return unicos, metricas
