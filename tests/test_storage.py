"""Testes de src/g1_scraper/storage.py."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from g1_scraper import storage
from g1_scraper.config import Config
from g1_scraper.models import Resultado, colunas


def _config(dir_saida, **kwargs):
    padrao = dict(
        termo="lgpd",
        size=10,
        max_paginas=1,
        timeout=(5, 30),
        pausa=0,
        tentativas=3,
        backoff=0,
        fuso="America/Sao_Paulo",
        dir_saida=dir_saida,
    )
    padrao.update(kwargs)
    return Config(**padrao)


def _resultado(**kwargs):
    padrao = dict(
        titulo="Proteção de dados em discussão no município",
        url="https://g1.globo.com/a.ghtml",
        resumo="…um resumo com ç, ã e —, para testar acentos…",
        data_publicacao="2026-08-31T14:30:11-03:00",
        data_atualizacao="2026-08-31T19:52:12-03:00",
        pagina=0,
        posicao=1,
        coletado_em="2026-09-17T10:00:00-03:00",
    )
    padrao.update(kwargs)
    return Resultado(**padrao)


def test_agora_tem_fuso_explicito():
    momento = storage.agora("America/Sao_Paulo")
    assert momento.tzinfo is not None
    assert momento.utcoffset() == ZoneInfo("America/Sao_Paulo").utcoffset(momento)


def test_carimbo_nao_tem_dois_pontos():
    momento = datetime(2026, 9, 17, 10, 30, 45, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert ":" not in storage.carimbo(momento)
    assert storage.carimbo(momento) == "20260917T103045"


def test_caminho_saida_usa_termo_e_carimbo(tmp_path):
    momento = datetime(2026, 9, 17, 10, 30, 45, tzinfo=ZoneInfo("America/Sao_Paulo"))
    caminho = storage.caminho_saida(_config(tmp_path, termo="LGPD"), momento, "csv")
    assert caminho.name == "g1_lgpd_20260917T103045.csv"


def test_caminho_saida_troca_espacos_e_pontuacao_por_underscore(tmp_path):
    momento = datetime(2026, 9, 17, 10, 30, 45, tzinfo=ZoneInfo("America/Sao_Paulo"))
    caminho = storage.caminho_saida(_config(tmp_path, termo="proteção de dados!"), momento, "csv")
    assert caminho.name == "g1_proteção_de_dados__20260917T103045.csv"


def test_salvar_csv_grava_e_le_com_acentos(tmp_path):
    registros = [_resultado()]
    caminho = tmp_path / "saida.csv"
    storage.salvar_csv(registros, caminho)

    with caminho.open(encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        assert leitor.fieldnames == list(colunas())
        linhas = list(leitor)

    assert linhas[0]["titulo"] == registros[0].titulo
    assert linhas[0]["resumo"] == registros[0].resumo


def test_salvar_json_preserva_none_como_null(tmp_path):
    registros = [_resultado(resumo=None, data_atualizacao=None)]
    caminho = tmp_path / "saida.json"
    storage.salvar_json(registros, caminho)

    dados = json.loads(caminho.read_text(encoding="utf-8"))
    assert dados[0]["resumo"] is None
    assert dados[0]["data_atualizacao"] is None
    assert dados[0]["titulo"] == registros[0].titulo


def test_hash_commit_devolve_none_quando_git_falha(monkeypatch):
    import subprocess

    def _levanta(*args, **kwargs):
        raise FileNotFoundError("git não encontrado")

    monkeypatch.setattr(subprocess, "run", _levanta)
    assert storage.hash_commit() is None


def test_versoes_inclui_os_pacotes_declarados():
    versoes = storage.versoes()
    assert set(versoes.keys()) == set(storage.PACOTES)
    assert all(isinstance(v, str) for v in versoes.values())


def test_salvar_manifesto_estrutura(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "hash_commit", lambda: "commit-fake")
    momento = datetime(2026, 9, 17, 10, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    caminho = tmp_path / "manifesto.json"
    metricas = {"registros_na_base": 16, "paginas_com_falha": 0}

    storage.salvar_manifesto(caminho, _config(tmp_path), momento, metricas)
    manifesto = json.loads(caminho.read_text(encoding="utf-8"))

    assert manifesto["commit"] == "commit-fake"
    assert manifesto["termo"] == "lgpd"
    assert manifesto["parametros"]["timeout"] == [5, 30]
    assert manifesto["metricas"] == metricas
    assert set(manifesto["versoes"].keys()) == set(storage.PACOTES)
