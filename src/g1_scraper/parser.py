"""Extração de registros a partir do JSON da API. Funções puras, sem efeito colateral."""

import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from g1_scraper.models import Resultado

ESPACOS = re.compile(r"\s+")
SEPARADOR = " — "


def extrair_hits(resposta: Any) -> list[dict[str, Any]]:
    """Devolve a lista de hits da resposta, ou lista vazia se a estrutura não vier."""
    try:
        return resposta[0]["result"]["hits"]["hits"]
    except (IndexError, KeyError, TypeError):
        return []


def extrair_total(resposta: Any) -> int | None:
    """Devolve `hits.total.value`, ou `None` se a chave não existir."""
    try:
        return resposta[0]["result"]["hits"]["total"]["value"]
    except (IndexError, KeyError, TypeError):
        return None


def limpar_texto(bruto: str | None) -> str | None:
    """Colapsa espaços e quebras de linha; devolve `None` se nada sobrar."""
    if not bruto:
        return None
    return ESPACOS.sub(" ", bruto).strip() or None


def eh_anuncio(hit: dict[str, Any]) -> bool:
    """Indica se o hit é publicidade (presença de `pubeditorial`)."""
    return "pubeditorial" in hit.get("_source", {})


def extrair_url_real(url_rastreamento: str | None) -> str | None:
    """Extrai a URL da matéria do parâmetro `u=` do link de rastreamento."""
    if not url_rastreamento:
        return None
    alvo = parse_qs(urlparse(url_rastreamento).query).get("u", [None])[0]
    return alvo or url_rastreamento


def formatar_fragmento(texto: str) -> str:
    """Envolve o fragmento em reticências, como o site exibe no card de resultado."""
    return f"...{texto.removesuffix('.')}..."


def extrair_resumo(hit: dict[str, Any]) -> str | None:
    """Monta o resumo a partir dos fragmentos de `highlight`, com `description` como
    alternativa. As tags `<em>` da marcação de busca são removidas com Beautiful Soup.

    Os fragmentos saem entre reticências e unidos por travessão, espelhando a
    apresentação do site; a alternativa `description` é gravada sem reticências.
    """
    fragmentos = hit.get("highlight", {}).get("body", [])
    textos = [
        formatar_fragmento(texto)
        for frag in fragmentos
        if (texto := limpar_texto(BeautifulSoup(frag, "html.parser").get_text()))
    ]
    if textos:
        return SEPARADOR.join(textos)
    return limpar_texto(hit.get("_source", {}).get("description"))


def normalizar_data(issued: str | None, fuso: str) -> str | None:
    """Converte `issued` para ISO 8601 no fuso de referência."""
    if not issued:
        return None
    try:
        momento = datetime.fromisoformat(issued)
    except ValueError:
        return None
    if momento.tzinfo is None:
        return None
    return momento.astimezone(ZoneInfo(fuso)).isoformat()


def hit_para_resultado(
    hit: dict[str, Any], pagina: int, posicao: int, coletado_em: str, fuso: str
) -> Resultado:
    """Converte um hit em `Resultado`. Campo ausente vira `None`, nunca exceção."""
    fonte = hit.get("_source", {})
    return Resultado(
        titulo=limpar_texto(fonte.get("title")),
        url=extrair_url_real(fonte.get("url")),
        resumo=extrair_resumo(hit),
        data_publicacao=normalizar_data(fonte.get("issued"), fuso),
        data_atualizacao=normalizar_data(fonte.get("modified"), fuso),
        pagina=pagina,
        posicao=posicao,
        coletado_em=coletado_em,
    )


def extrair_registros(
    resposta: Any, pagina: int, coletado_em: str, fuso: str
) -> tuple[list[Resultado], int]:
    """Converte uma resposta inteira em registros, sem os anúncios.

    Devolve os registros e a quantidade de anúncios descartados.
    """
    registros: list[Resultado] = []
    anuncios = 0
    for indice, hit in enumerate(extrair_hits(resposta), start=1):
        if eh_anuncio(hit):
            anuncios += 1
            continue
        registros.append(hit_para_resultado(hit, pagina, indice, coletado_em, fuso))
    return registros, anuncios
