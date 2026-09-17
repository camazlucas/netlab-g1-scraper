"""Testes de src/g1_scraper/__main__.py.

configurar_log, coletar, salvar_csv, salvar_json e salvar_manifesto são
mockados: aqui o alvo é a orquestração da CLI (argumentos, código de saída,
quais arquivos são gravados), não a coleta nem a gravação em si.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from g1_scraper import __main__ as cli
from g1_scraper.models import Resultado


def _registro():
    return Resultado(
        titulo="t",
        url="https://g1.globo.com/a.ghtml",
        resumo=None,
        data_publicacao=None,
        data_atualizacao=None,
        pagina=0,
        posicao=1,
        coletado_em="2026-09-17T10:00:00-03:00",
    )


def _isolar_io(monkeypatch, registros, metricas=None):
    """Evita logging real e escrita em disco; devolve os arquivos "gravados"."""
    metricas = metricas or {
        "registros_na_base": len(registros),
        "paginas_coletadas": 1,
        "paginas_com_falha": 0,
        "duplicados_descartados": 0,
        "anuncios_filtrados": 0,
        "campos_ausentes": {},
        "motivo_parada": "ok",
    }
    chamadas = {}

    monkeypatch.setattr(cli, "configurar_log", lambda caminho, verboso: None)
    monkeypatch.setattr(
        cli,
        "agora",
        lambda fuso: datetime(2026, 9, 17, 10, 0, 0, tzinfo=ZoneInfo(fuso)),
    )
    monkeypatch.setattr(cli, "coletar", lambda config: (registros, metricas))
    monkeypatch.setattr(
        cli, "salvar_csv", lambda regs, caminho: chamadas.setdefault("csv", caminho)
    )
    monkeypatch.setattr(
        cli, "salvar_json", lambda regs, caminho: chamadas.setdefault("json", caminho)
    )
    monkeypatch.setattr(
        cli,
        "salvar_manifesto",
        lambda caminho, config, momento, met: chamadas.setdefault("manifesto", caminho),
    )
    return chamadas


def test_devolve_1_com_base_vazia(monkeypatch, tmp_path):
    _isolar_io(monkeypatch, registros=[])
    codigo = cli.main(["--dir-saida", str(tmp_path)])
    assert codigo == 1


def test_devolve_0_com_registros(monkeypatch, tmp_path):
    _isolar_io(monkeypatch, registros=[_registro()])
    codigo = cli.main(["--dir-saida", str(tmp_path)])
    assert codigo == 0


def test_formato_csv_nao_grava_json(monkeypatch, tmp_path):
    chamadas = _isolar_io(monkeypatch, registros=[_registro()])
    cli.main(["--dir-saida", str(tmp_path), "--formato", "csv"])
    assert "csv" in chamadas
    assert "json" not in chamadas


def test_formato_json_nao_grava_csv(monkeypatch, tmp_path):
    chamadas = _isolar_io(monkeypatch, registros=[_registro()])
    cli.main(["--dir-saida", str(tmp_path), "--formato", "json"])
    assert "json" in chamadas
    assert "csv" not in chamadas


def test_formato_padrao_ambos_grava_csv_e_json(monkeypatch, tmp_path):
    chamadas = _isolar_io(monkeypatch, registros=[_registro()])
    cli.main(["--dir-saida", str(tmp_path)])
    assert "csv" in chamadas
    assert "json" in chamadas


def test_manifesto_e_gravado_mesmo_com_base_vazia(monkeypatch, tmp_path):
    chamadas = _isolar_io(monkeypatch, registros=[])
    cli.main(["--dir-saida", str(tmp_path)])
    assert "manifesto" in chamadas


def test_argumentos_customizados_chegam_no_config(monkeypatch, tmp_path):
    configs_usados = []
    monkeypatch.setattr(cli, "configurar_log", lambda caminho, verboso: None)
    monkeypatch.setattr(
        cli,
        "agora",
        lambda fuso: datetime(2026, 9, 17, 10, 0, 0, tzinfo=ZoneInfo(fuso)),
    )

    def _coletar_falso(config):
        configs_usados.append(config)
        return [], {
            "registros_na_base": 0,
            "paginas_coletadas": 0,
            "paginas_com_falha": 0,
            "duplicados_descartados": 0,
            "anuncios_filtrados": 0,
            "campos_ausentes": {},
            "motivo_parada": "teste",
        }

    monkeypatch.setattr(cli, "coletar", _coletar_falso)
    monkeypatch.setattr(cli, "salvar_csv", lambda *a, **k: None)
    monkeypatch.setattr(cli, "salvar_json", lambda *a, **k: None)
    monkeypatch.setattr(cli, "salvar_manifesto", lambda *a, **k: None)

    cli.main(["--termo", "proteção de dados", "--size", "20", "--dir-saida", str(tmp_path)])

    assert configs_usados[0].termo == "proteção de dados"
    assert configs_usados[0].size == 20


def test_resumir_com_zero_registros():
    metricas = {
        "registros_na_base": 0,
        "paginas_coletadas": 0,
        "paginas_com_falha": 2,
        "duplicados_descartados": 0,
        "anuncios_filtrados": 0,
        "campos_ausentes": {},
        "motivo_parada": "3 falhas consecutivas (from=0)",
    }
    linha = cli.resumir(metricas)
    assert linha.startswith("0 registros na base")
    assert "3 falhas consecutivas" in linha


def test_resumir_lista_so_os_campos_ausentes_com_contagem_maior_que_zero():
    metricas = {
        "registros_na_base": 5,
        "paginas_coletadas": 1,
        "paginas_com_falha": 0,
        "duplicados_descartados": 0,
        "anuncios_filtrados": 0,
        "campos_ausentes": {"resumo": 2, "data_publicacao": 0},
        "motivo_parada": "limite de páginas atingido",
    }
    linha = cli.resumir(metricas)
    assert "resumo=2" in linha
    assert "data_publicacao" not in linha
