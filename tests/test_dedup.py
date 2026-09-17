"""Testes de src/g1_scraper/dedup.py."""

from __future__ import annotations

from g1_scraper import dedup
from g1_scraper.models import Resultado


def _registro(url, titulo="titulo", posicao=1):
    return Resultado(
        titulo=titulo,
        url=url,
        resumo=None,
        data_publicacao=None,
        data_atualizacao=None,
        pagina=0,
        posicao=posicao,
        coletado_em="2026-09-17T10:00:00-03:00",
    )


def test_url_repetida_e_descartada_uma_vez():
    registros = [
        _registro("https://g1.globo.com/a.ghtml", posicao=1),
        _registro("https://g1.globo.com/a.ghtml", posicao=2),
    ]
    unicos, duplicados, sem_url = dedup.deduplicar(registros)
    assert len(unicos) == 1
    assert duplicados == 1
    assert sem_url == 0


def test_chave_normaliza_esquema_e_dominio_mas_nao_o_caminho():
    assert dedup.chave("HTTPS://G1.GLOBO.COM/a.ghtml") == dedup.chave(
        "https://g1.globo.com/a.ghtml"
    )
    assert dedup.chave("https://g1.globo.com/A.ghtml") != dedup.chave(
        "https://g1.globo.com/a.ghtml"
    )


def test_titulos_quase_identicos_com_urls_diferentes_nao_sao_fundidos():
    registros = [
        _registro("https://g1.globo.com/video-vazamento.ghtml", titulo="Vazamento de dados na BA"),
        _registro(
            "https://g1.globo.com/noticia-vazamento.ghtml", titulo="Vazamento de dados na BA"
        ),
    ]
    unicos, duplicados, sem_url = dedup.deduplicar(registros)
    assert len(unicos) == 2
    assert duplicados == 0


def test_registro_sem_url_e_mantido_e_contado():
    registros = [_registro(None), _registro("https://g1.globo.com/a.ghtml")]
    unicos, duplicados, sem_url = dedup.deduplicar(registros)
    assert len(unicos) == 2
    assert sem_url == 1


def test_chave_none_para_url_none():
    assert dedup.chave(None) is None
