"""Testes de src/g1_scraper/scraper.py.

buscar_pagina, extrair_total, extrair_hits e extrair_registros são mockados
via monkeypatch: o objetivo aqui é o laço de orquestração (scraper.py), não
o parsing em si (já coberto em test_parser.py).
"""

from __future__ import annotations

from g1_scraper import scraper
from g1_scraper.config import Config
from g1_scraper.models import Resultado


def _config(**kwargs):
    padrao = dict(
        termo="lgpd",
        size=10,
        max_paginas=5,
        timeout=(5, 30),
        pausa=0,
        tentativas=3,
        backoff=0,
        fuso="America/Sao_Paulo",
        dir_saida=None,
    )
    padrao.update(kwargs)
    return Config(**padrao)


def _registro(url, posicao=1):
    return Resultado(
        titulo="t",
        url=url,
        resumo=None,
        data_publicacao=None,
        data_atualizacao=None,
        pagina=0,
        posicao=posicao,
        coletado_em="2026-09-17T10:00:00-03:00",
    )


def test_acumula_registros_entre_paginas_b1(monkeypatch):
    """O bug B1 era `resultados = dados_pagina` (sobrescreve). Aqui confere
    que scraper.py usa extend e preserva as duas páginas."""
    respostas = {0: {"hits": ["h1", "h2"]}, 10: {"hits": ["h3"]}}
    registros_por_pagina = {
        0: (
            [
                _registro("https://g1.globo.com/1.ghtml"),
                _registro("https://g1.globo.com/2.ghtml", 2),
            ],
            0,
        ),
        1: ([_registro("https://g1.globo.com/3.ghtml")], 0),
    }

    monkeypatch.setattr(scraper, "buscar_pagina", lambda s, c, inicio: respostas[inicio])
    monkeypatch.setattr(scraper, "extrair_total", lambda r: 1219)
    monkeypatch.setattr(scraper, "extrair_hits", lambda r: r["hits"])
    monkeypatch.setattr(
        scraper,
        "extrair_registros",
        lambda r, pagina, coletado_em, fuso: registros_por_pagina[pagina],
    )

    unicos, metricas = scraper.coletar(_config(max_paginas=2), sessao=object())

    assert len(unicos) == 3
    assert metricas["paginas_coletadas"] == 2
    assert metricas["paginas_com_falha"] == 0


def test_para_quando_hits_ausente(monkeypatch):
    monkeypatch.setattr(scraper, "buscar_pagina", lambda s, c, inicio: {"hits": []})
    monkeypatch.setattr(scraper, "extrair_total", lambda r: 1219)
    monkeypatch.setattr(scraper, "extrair_hits", lambda r: r["hits"])
    monkeypatch.setattr(scraper, "extrair_registros", lambda *a, **k: ([], 0))

    unicos, metricas = scraper.coletar(_config(max_paginas=5), sessao=object())

    assert metricas["paginas_coletadas"] == 0
    assert "sem hits" in metricas["motivo_parada"]


def test_para_quando_from_maior_ou_igual_ao_total(monkeypatch):
    monkeypatch.setattr(scraper, "buscar_pagina", lambda s, c, inicio: {"hits": ["h"]})
    monkeypatch.setattr(scraper, "extrair_total", lambda r: 15)
    monkeypatch.setattr(scraper, "extrair_hits", lambda r: r["hits"])
    monkeypatch.setattr(
        scraper,
        "extrair_registros",
        lambda *a, **k: ([_registro("https://g1.globo.com/x.ghtml")], 0),
    )

    unicos, metricas = scraper.coletar(_config(max_paginas=5, size=10), sessao=object())

    assert metricas["paginas_coletadas"] == 2  # from=0 e from=10; from=20>=15 encerra
    assert "fim do conjunto" in metricas["motivo_parada"]


def test_para_no_teto_da_api(monkeypatch):
    monkeypatch.setattr(scraper, "buscar_pagina", lambda s, c, inicio: {"hits": ["h"]})
    monkeypatch.setattr(scraper, "extrair_total", lambda r: 999_999)
    monkeypatch.setattr(scraper, "extrair_hits", lambda r: r["hits"])
    monkeypatch.setattr(scraper, "extrair_registros", lambda *a, **k: ([], 0))

    config = _config(max_paginas=100, size=9_990)
    unicos, metricas = scraper.coletar(config, sessao=object())

    assert metricas["motivo_parada"] == "teto da API alcançado (from=9990)"


def test_falhas_consecutivas_maximas_interrompem_a_coleta(monkeypatch):
    monkeypatch.setattr(scraper, "buscar_pagina", lambda s, c, inicio: None)

    unicos, metricas = scraper.coletar(_config(max_paginas=10), sessao=object())

    assert metricas["paginas_com_falha"] == scraper.FALHAS_CONSECUTIVAS_MAX
    assert "falhas consecutivas" in metricas["motivo_parada"]
    assert unicos == []


def test_falha_isolada_nao_interrompe_a_coleta(monkeypatch):
    respostas = {0: None, 10: {"hits": ["h"]}}
    monkeypatch.setattr(scraper, "buscar_pagina", lambda s, c, inicio: respostas[inicio])
    monkeypatch.setattr(scraper, "extrair_total", lambda r: 1219)
    monkeypatch.setattr(scraper, "extrair_hits", lambda r: r["hits"])
    monkeypatch.setattr(
        scraper,
        "extrair_registros",
        lambda *a, **k: ([_registro("https://g1.globo.com/y.ghtml")], 0),
    )

    unicos, metricas = scraper.coletar(_config(max_paginas=2), sessao=object())

    assert metricas["paginas_com_falha"] == 1
    assert metricas["paginas_coletadas"] == 1
    assert len(unicos) == 1


def test_deduplica_e_conta_metricas(monkeypatch):
    monkeypatch.setattr(scraper, "buscar_pagina", lambda s, c, inicio: {"hits": ["h"]})
    monkeypatch.setattr(scraper, "extrair_total", lambda r: 10)
    monkeypatch.setattr(scraper, "extrair_hits", lambda r: r["hits"])
    monkeypatch.setattr(
        scraper,
        "extrair_registros",
        lambda *a, **k: (
            [
                _registro("https://g1.globo.com/z.ghtml"),
                _registro("https://g1.globo.com/z.ghtml", 2),
            ],
            3,
        ),
    )

    unicos, metricas = scraper.coletar(_config(max_paginas=1), sessao=object())

    assert metricas["registros_brutos"] == 2
    assert metricas["registros_na_base"] == 1
    assert metricas["duplicados_descartados"] == 1
    assert metricas["anuncios_filtrados"] == 3
