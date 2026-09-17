"""Ponto de entrada da coleta: interface de linha de comando e configuração de log."""

import argparse
import logging
import sys
from pathlib import Path

from g1_scraper.config import Config
from g1_scraper.scraper import coletar
from g1_scraper.storage import (
    agora,
    caminho_saida,
    carimbo,
    salvar_csv,
    salvar_json,
    salvar_manifesto,
)

logger = logging.getLogger("g1_scraper")

FORMATO_LOG = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configurar_log(caminho: Path, verboso: bool) -> None:
    """Configura o log em dois destinos: console e arquivo."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    raiz = logging.getLogger()
    raiz.setLevel(logging.DEBUG if verboso else logging.INFO)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if verboso else logging.INFO)
    console.setFormatter(logging.Formatter(FORMATO_LOG))

    arquivo = logging.FileHandler(caminho, encoding="utf-8")
    arquivo.setLevel(logging.DEBUG)
    arquivo.setFormatter(logging.Formatter(FORMATO_LOG))

    raiz.handlers = [console, arquivo]


def montar_argumentos() -> argparse.ArgumentParser:
    """Define os argumentos aceitos pela linha de comando."""
    parser = argparse.ArgumentParser(
        prog="g1-scraper",
        description="Coleta resultados da busca do G1 e grava em CSV e/ou JSON.",
    )
    padrao = Config()
    parser.add_argument("--termo", default=padrao.termo, help="termo buscado")
    parser.add_argument("--size", type=int, default=padrao.size, help="itens por página")
    parser.add_argument(
        "--max-paginas", type=int, default=padrao.max_paginas, help="trava de segurança"
    )
    parser.add_argument("--pausa", type=float, default=padrao.pausa, help="segundos entre páginas")
    parser.add_argument(
        "--formato", choices=("csv", "json", "ambos"), default="ambos", help="formato de saída"
    )
    parser.add_argument(
        "--dir-saida", type=Path, default=padrao.dir_saida, help="diretório dos arquivos gerados"
    )
    parser.add_argument("-v", "--verboso", action="store_true", help="log em nível DEBUG")
    return parser


def resumir(metricas: dict) -> str:
    """Monta a linha de resumo final da execução."""
    ausentes = ", ".join(f"{campo}={n}" for campo, n in metricas["campos_ausentes"].items() if n)
    return (
        f"{metricas['registros_na_base']} registros na base | "
        f"{metricas['paginas_coletadas']} páginas ok, {metricas['paginas_com_falha']} com falha | "
        f"{metricas['duplicados_descartados']} duplicados, "
        f"{metricas['anuncios_filtrados']} anúncios filtrados | "
        f"campos ausentes: {ausentes or 'nenhum'} | "
        f"parada: {metricas['motivo_parada']}"
    )


def main(argv: list[str] | None = None) -> int:
    """Executa a coleta. Devolve 0 em caso de sucesso e 1 se nada for coletado."""
    args = montar_argumentos().parse_args(argv)
    config = Config(
        termo=args.termo,
        size=args.size,
        max_paginas=args.max_paginas,
        pausa=args.pausa,
        dir_saida=args.dir_saida,
    )

    momento = agora(config.fuso)
    configurar_log(config.dir_saida / f"coleta_{carimbo(momento)}.log", args.verboso)
    logger.info("iniciando coleta | termo=%r size=%d", config.termo, config.size)

    registros, metricas = coletar(config)

    if args.formato in ("csv", "ambos"):
        salvar_csv(registros, caminho_saida(config, momento, "csv"))
    if args.formato in ("json", "ambos"):
        salvar_json(registros, caminho_saida(config, momento, "json"))
    salvar_manifesto(
        config.dir_saida / f"manifesto_{carimbo(momento)}.json", config, momento, metricas
    )

    logger.info("coleta finalizada: %s", resumir(metricas))
    return 0 if registros else 1


if __name__ == "__main__":
    raise SystemExit(main())
