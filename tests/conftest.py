"""Fixtures compartilhadas para os testes do g1_scraper.

Fixtures de arquivo (snapshots reais, em data/) simulam respostas da API sem
tocar rede. Fixtures de hit derivam de casos reais de
data/reference/snapshot_from_0.json, cobrindo situacoes que o snapshot
inteiro nao isola sozinho (campo ausente, por exemplo).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
DIR_REFERENCIA = RAIZ / "data" / "reference"
DIR_BASELINE_API = RAIZ / "data" / "baseline" / "api"


def _carregar_json(caminho: Path) -> dict:
    with caminho.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


# --- Snapshots reais (data/reference/) ---------------------------------


@pytest.fixture
def snapshot_from_0() -> dict:
    """from=0: usado para comparar com a amostra manual (posicoes, anuncios,
    resumo, casamento por URL)."""
    return _carregar_json(DIR_REFERENCIA / "snapshot_from_0.json")


@pytest.fixture
def snapshot_from_10() -> dict:
    return _carregar_json(DIR_REFERENCIA / "snapshot_from_10.json")


@pytest.fixture
def snapshot_from_20() -> dict:
    return _carregar_json(DIR_REFERENCIA / "snapshot_from_20.json")


# --- Respostas de paginacao (data/baseline/api/) ------------------------


@pytest.fixture
def resposta_from_1219() -> dict:
    """from=1219: HTTP 200, mas hits.hits NAO existe (nao e lista vazia).
    E o caso real de parada -- um `.get("hits", [])` ingenuo esconderia
    a diferenca entre "acabou" e "resposta com formato inesperado"."""
    return _carregar_json(DIR_BASELINE_API / "paginacao_from_1219.json")


@pytest.fixture
def resposta_from_1220() -> dict:
    return _carregar_json(DIR_BASELINE_API / "paginacao_from_1220.json")


@pytest.fixture
def resposta_lista_vazia() -> dict:
    """Formato com hits.hits == [] explicitamente. Nao e o que a API faz de
    verdade no fim da paginacao (ela omite a chave), mas o codigo deve
    tratar os dois formatos -- por robustez, nao porque foi observado."""
    return {"result": {"hits": {"total": {"value": 1219}, "hits": []}}}


# --- Hits reais, adaptados de data/reference/snapshot_from_0.json -------
#
# hit_base e a ultima materia do snapshot (posicao 10, sem pubeditorial).
# As variantes "sem_*" sao esse mesmo hit com uma chave removida.

_HIT_BASE_URL = (
    "https://measures.globo.com/v1/click?c=busca-headless"
    "&h=37358a1913a853043b1b65c36ab8ac1760711440eb946c83ca1113ce2dd53d2"
    "603610b64bd752875e0f6c52ce856382f5f6cb60020e641316492b4fdd3f463f9"
    "&k=globocom.busca-headless&pa=1&po=10&q=lgpd&qid=g1.info_query_recency"
    "&rid=38899d19620ed0073b38ccac6c572676&t=g1&ts=1789589661"
    "&u=https%3A%2F%2Fg1.globo.com%2Feconomia%2Fnoticia%2F2026%2F08%2F31%2F"
    "governo-quer-padronizar-uso-de-biometria-em-portos-e-aeroportos.ghtml"
)


@pytest.fixture
def hit_base() -> dict:
    """Materia real e completa (posicao 10 do snapshot from=0), com
    highlight, issued e modified presentes. Usada como ponto de partida
    para os testes de campo ausente."""
    return {
        "_id": "hit-base-teste",
        "_source": {
            "title": (
                "Governo lança medidas para padronizar uso de biometria em portos e aeroportos"
            ),
            "issued": "2026-08-31T17:30:11.675Z",
            "modified": "2026-08-31T22:52:12.712Z",
            "species": "Matéria",
            "url": _HIT_BASE_URL,
        },
        "highlight": {
            "body": [
                "O processo será guiado pela Lei Geral de Proteção de "
                "Dados (<em>LGPD</em>), garantiu o ministério, e será "
                "supervisionado pela Autoridade Nacional"
            ]
        },
    }


@pytest.fixture
def hit_sem_highlight(hit_base: dict) -> dict:
    """hit_base sem a chave 'highlight' -- resumo deve sair None, sem
    excecao. (O bug original era AttributeError em
    card.find(...).get_text() quando o campo faltava.)"""
    hit = json.loads(json.dumps(hit_base))
    del hit["highlight"]
    return hit


@pytest.fixture
def hit_sem_issued(hit_base: dict) -> dict:
    """hit_base sem 'issued' -- data_publicacao deve sair None."""
    hit = json.loads(json.dumps(hit_base))
    del hit["_source"]["issued"]
    return hit


@pytest.fixture
def hit_sem_modified(hit_base: dict) -> dict:
    """hit_base sem 'modified' -- data_atualizacao deve sair None. Como o
    G1 exibe 'modified' no card, esse item tambem ficaria fora do
    casamento com a amostra manual (limitacao do dado, nao do parser)."""
    hit = json.loads(json.dumps(hit_base))
    del hit["_source"]["modified"]
    return hit


# --- Hit de video (schema diferente), real (posicao 2 do snapshot) -----


@pytest.fixture
def hit_video() -> dict:
    """Especie 'Vídeo On Demand': sem caption/summaryBlocks/section/
    highlight; tem description, program, site. O resumo vem de
    'description', sem as reticencias que marcam fragmentos de highlight."""
    return {
        "_id": "14903650",
        "_source": {
            "SizeOrDuration": 1138304,
            "description": (
                "Falhas na proteção de dados podem facilitar golpes e "
                "outros crimes. Veja esse e outros destaques do quadro."
            ),
            "issued": "2026-08-26T13:27:11-03:00",
            "modified": "2026-08-26T13:52:03-03:00",
            "program": "MGTV 1ª Edição – Zona da Mata",
            "publisher": "GloboVideos",
            "site": "MGTV 1ª Edição – Zona da Mata",
            "species": "Vídeo On Demand",
            "subscriberOnly": False,
            "title": (
                "Integração TEC: mais de 37% dos órgãos e empresas não seguem regras da LGPD"
            ),
            "url": (
                "https://measures.globo.com/v1/click?c=busca-headless"
                "&h=82e4e69c50d9cc8ababaf30c92e9150c42f97766a32e32706e4a78b"
                "4b2586ed48c9469e27c7be46f7ed6d5a41872d2077cbef1f61857928e"
                "001d36a5e06bad04&k=globocom.busca-headless&pa=1&po=2"
                "&q=lgpd&qid=g1.info_query_recency"
                "&rid=38899d19620ed0073b38ccac6c572676&t=g1&ts=1789589661"
                "&u=https%3A%2F%2Fg1.globo.com%2Fmg%2Fzona-da-mata%2Fmg1-"
                "zona-da-mata%2Fvideo%2Fintegracao-tec-mais-de-37-dos-"
                "orgaos-e-empresas-nao-seguem-regras-da-lgpd-14903650.ghtml"
            ),
        },
    }


# --- Hit de anuncio, real (posicao 1 do snapshot) -----------------------
#
# pubeditorial e um OBJETO, nao um booleano -- eh_anuncio() deve checar
# presenca da chave, nao um valor especifico. Este hit tambem tem
# 'highlight', o que confirma que o filtro precisa ser independente disso.


@pytest.fixture
def hit_anuncio() -> dict:
    """Tem 'pubeditorial' (objeto, nao bool) -- deve ser filtrado da base,
    mas contado na posicao (posicao e base 1, contada ANTES do filtro)."""
    return {
        "_id": "16db85c0-adca-4015-8ab0-657c7159ad9f",
        "_source": {
            "issued": "2026-09-16T13:21:02.671Z",
            "modified": "2026-09-16T13:21:02.948Z",
            "pubeditorial": {
                "anunciante": {"nome": "Prefeitura de Atibaia"},
                "data_vencimento": "2019-11-30T18:41:00.000Z",
                "nome": "Prefeitura de Atibaia 0411 - 2",
            },
            "section": [
                "G1",
                "SP",
                "Vale do Paraíba e Região",
                "Especial Publicitário",
                "Especial Publicitário - Prefeitura de Atibaia",
                "Notícias de Atibaia",
            ],
            "species": "Matéria",
            "title": ("Atibaia realiza 1º Encontro sobre Esclerose Múltipla e lança cadastro"),
            "url": (
                "https://measures.globo.com/v1/click?c=busca-headless"
                "&h=78060483863b6086a68e8a2cd2782103ee632fce34b5ab612c55d"
                "19375608b1c849c718687f5ec6d44f15069833efbeea251440b9ae93"
                "6c4e20d2e0a26f87f08&k=globocom.busca-headless&pa=1&po=1"
                "&q=lgpd&qid=g1.info_query_recency"
                "&rid=38899d19620ed0073b38ccac6c572676&t=g1&ts=1789589661"
                "&u=https%3A%2F%2Fg1.globo.com%2Fsp%2Fvale-do-paraiba-"
                "regiao%2Fespecial-publicitario%2Fprefeitura-de-atibaia%2F"
                "noticias-de-atibaia%2Fnoticia%2F2026%2F09%2F16%2F"
                "atibaia-realiza-1o-encontro-sobre-esclerose-multipla-e-"
                "lanca-cadastro.ghtml"
            ),
        },
        "highlight": {
            "body": [
                "Todas as respostas fornecidas serão tratadas de forma "
                "sigilosa, em conformidade com as disposições da Lei "
                "Geral de Proteção de Dados (<em>LGPD</em>"
            ]
        },
    }


# --- Mocks para client.py (sem tocar rede) --------------------------------


class RespostaFalsa:
    """Estrutura minima para simular requests.Response nos testes de
    client.py, sem precisar de uma classe nova por caso de status HTTP."""

    def __init__(self, status_code: int, corpo: dict | None = None) -> None:
        self.status_code = status_code
        self._corpo = corpo or {}

    def json(self) -> dict:
        return self._corpo

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests

            erro = requests.HTTPError(f"status {self.status_code}")
            erro.response = self
            raise erro


@pytest.fixture
def resposta_falsa():
    """Fabrica de RespostaFalsa -- uso: resposta_falsa(403) ou
    resposta_falsa(200, {"result": {...}})."""
    return RespostaFalsa
