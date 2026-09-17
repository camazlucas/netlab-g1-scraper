"""Gravação da base coletada em CSV e JSON, com manifesto da execução."""

import csv
import json
import logging
import subprocess
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from g1_scraper.config import RAIZ, Config
from g1_scraper.models import Resultado, colunas

logger = logging.getLogger(__name__)

PACOTES = ("requests", "beautifulsoup4")


def agora(fuso: str) -> datetime:
    """Devolve o instante atual com fuso explícito (nunca um datetime naive)."""
    return datetime.now(ZoneInfo(fuso))


def carimbo(momento: datetime) -> str:
    """Formata o instante para uso em nome de arquivo (sem `:`, proibido no Windows)."""
    return momento.strftime("%Y%m%dT%H%M%S")


def caminho_saida(config: Config, momento: datetime, extensao: str) -> Path:
    """Monta o caminho do arquivo de saída, com termo e carimbo de tempo no nome."""
    termo = "".join(c if c.isalnum() else "_" for c in config.termo.lower())
    return config.dir_saida / f"g1_{termo}_{carimbo(momento)}.{extensao}"


def salvar_csv(registros: list[Resultado], caminho: Path) -> Path:
    """Grava os registros em CSV, com as colunas derivadas de `Resultado`."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas())
        escritor.writeheader()
        escritor.writerows(asdict(registro) for registro in registros)
    logger.info("CSV gravado: %s (%d registros)", caminho, len(registros))
    return caminho


def salvar_json(registros: list[Resultado], caminho: Path) -> Path:
    """Grava os registros em JSON, preservando `None` como `null`."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(
            [asdict(registro) for registro in registros],
            arquivo,
            ensure_ascii=False,
            indent=2,
        )
    logger.info("JSON gravado: %s (%d registros)", caminho, len(registros))
    return caminho


def hash_commit() -> str | None:
    """Devolve o commit atual do repositório, ou `None` se não for possível obtê-lo."""
    try:
        resultado = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        logger.warning("commit indisponível: manifesto sairá sem o hash")
        return None
    return resultado.stdout.strip() or None


def versoes() -> dict[str, str]:
    """Devolve as versões das bibliotecas relevantes para a coleta."""
    from importlib.metadata import PackageNotFoundError, version

    encontradas = {}
    for pacote in PACOTES:
        try:
            encontradas[pacote] = version(pacote)
        except PackageNotFoundError:
            encontradas[pacote] = "desconhecida"
    return encontradas


def salvar_manifesto(
    caminho: Path, config: Config, momento: datetime, metricas: dict[str, Any]
) -> Path:
    """Grava o manifesto da execução ao lado da base, para rastreabilidade."""
    manifesto = {
        "executado_em": momento.isoformat(),
        "commit": hash_commit(),
        "termo": config.termo,
        "parametros": {
            "size": config.size,
            "max_paginas": config.max_paginas,
            "pausa": config.pausa,
            "timeout": list(config.timeout),
            "fuso": config.fuso,
        },
        "metricas": metricas,
        "versoes": versoes(),
    }
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(manifesto, arquivo, ensure_ascii=False, indent=2)
    logger.info("manifesto gravado: %s", caminho)
    return caminho
