"""Testes de src/g1_scraper/parser.py."""

from __future__ import annotations

from g1_scraper import parser


def test_extrair_resumo_hit_normal(hit_base):
    resumo = parser.extrair_resumo(hit_base)
    assert resumo == (
        "...O processo será guiado pela Lei Geral de Proteção de Dados "
        "(LGPD), garantiu o ministério, e será supervisionado pela "
        "Autoridade Nacional..."
    )


def test_extrair_resumo_sem_highlight(hit_sem_highlight):
    assert parser.extrair_resumo(hit_sem_highlight) is None


def test_extrair_resumo_video_usa_description(hit_video):
    resumo = parser.extrair_resumo(hit_video)
    assert resumo == (
        "Falhas na proteção de dados podem facilitar golpes e outros "
        "crimes. Veja esse e outros destaques do quadro."
    )
    assert "…" not in resumo


def test_data_publicacao_ausente_vira_none(hit_sem_issued):
    resultado = parser.hit_para_resultado(
        hit_sem_issued,
        pagina=0,
        posicao=1,
        coletado_em="2026-09-17T10:00:00-03:00",
        fuso="America/Sao_Paulo",
    )
    assert resultado.data_publicacao is None


def test_data_atualizacao_ausente_vira_none(hit_sem_modified):
    resultado = parser.hit_para_resultado(
        hit_sem_modified,
        pagina=0,
        posicao=1,
        coletado_em="2026-09-17T10:00:00-03:00",
        fuso="America/Sao_Paulo",
    )
    assert resultado.data_atualizacao is None


def test_eh_anuncio_true_para_hit_com_pubeditorial(hit_anuncio):
    assert parser.eh_anuncio(hit_anuncio) is True


def test_eh_anuncio_false_para_hit_normal(hit_base):
    assert parser.eh_anuncio(hit_base) is False


def test_extrair_url_real_decodifica_parametro_u(hit_base):
    url_rastreamento = hit_base["_source"]["url"]
    url_real = parser.extrair_url_real(url_rastreamento)
    assert url_real == (
        "https://g1.globo.com/economia/noticia/2026/08/31/"
        "governo-quer-padronizar-uso-de-biometria-em-portos-e-aeroportos.ghtml"
    )


def test_extrair_url_real_sem_parametro_u_usa_fallback():
    url = "https://measures.globo.com/v1/click?pa=1"
    assert parser.extrair_url_real(url) == url


def test_extrair_url_real_none_devolve_none():
    assert parser.extrair_url_real(None) is None


def test_normalizar_data_z_e_offset_convergem():
    em_z = parser.normalizar_data("2026-08-31T22:52:12.712Z", "America/Sao_Paulo")
    em_offset = parser.normalizar_data("2026-08-31T19:52:12.712-03:00", "America/Sao_Paulo")
    assert em_z == em_offset


def test_normalizar_data_none_devolve_none():
    assert parser.normalizar_data(None, "America/Sao_Paulo") is None
