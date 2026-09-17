"""Testes de src/g1_scraper/client.py."""

from __future__ import annotations

from unittest.mock import Mock

import requests

from g1_scraper import client
from g1_scraper.config import Config


def _config(**kwargs):
    padrao = dict(
        termo="lgpd",
        size=10,
        max_paginas=1,
        timeout=(5, 30),
        pausa=0,
        tentativas=3,
        backoff=0,
        fuso="America/Sao_Paulo",
        dir_saida="data/output",
    )
    padrao.update(kwargs)
    return Config(**padrao)


def test_sucesso_devolve_json(resposta_falsa):
    sessao = Mock()
    sessao.post.return_value = resposta_falsa(200, {"resultado": "ok"})
    resposta = client.buscar_pagina(sessao, _config(), inicio=0)
    assert resposta == {"resultado": "ok"}
    assert sessao.post.call_count == 1


def test_timeout_devolve_none_sem_derrubar_execucao():
    sessao = Mock()
    sessao.post.side_effect = requests.Timeout()
    assert client.buscar_pagina(sessao, _config(), inicio=0) is None


def test_connection_error_devolve_none():
    sessao = Mock()
    sessao.post.side_effect = requests.ConnectionError()
    assert client.buscar_pagina(sessao, _config(), inicio=0) is None


def test_400_nao_e_retentavel_falha_sem_retry(resposta_falsa):
    sessao = Mock()
    sessao.post.return_value = resposta_falsa(400)
    assert client.buscar_pagina(sessao, _config(tentativas=3), inicio=10_000) is None
    assert sessao.post.call_count == 1


def test_403_nao_e_retentavel_falha_sem_retry(resposta_falsa):
    sessao = Mock()
    sessao.post.return_value = resposta_falsa(403)
    assert client.buscar_pagina(sessao, _config(tentativas=3), inicio=0) is None
    assert sessao.post.call_count == 1


def test_500_e_retentavel_tenta_de_novo_e_depois_funciona(resposta_falsa):
    sessao = Mock()
    sessao.post.side_effect = [
        resposta_falsa(500),
        resposta_falsa(200, {"resultado": "ok"}),
    ]
    resposta = client.buscar_pagina(sessao, _config(tentativas=3), inicio=0)
    assert resposta == {"resultado": "ok"}
    assert sessao.post.call_count == 2


def test_500_esgota_tentativas_devolve_none(resposta_falsa):
    sessao = Mock()
    sessao.post.return_value = resposta_falsa(500)
    assert client.buscar_pagina(sessao, _config(tentativas=3), inicio=0) is None
    assert sessao.post.call_count == 3


def test_429_e_retentavel(resposta_falsa):
    sessao = Mock()
    sessao.post.side_effect = [
        resposta_falsa(429),
        resposta_falsa(200, {"ok": True}),
    ]
    resposta = client.buscar_pagina(sessao, _config(tentativas=3), inicio=0)
    assert resposta == {"ok": True}
    assert sessao.post.call_count == 2


def test_criar_sessao_devolve_session():
    assert isinstance(client.criar_sessao(), requests.Session)
