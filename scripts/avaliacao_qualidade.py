"""Avaliação da qualidade da base final da etapa 8.

Casa a base coletada com as referências de 16/09 (snapshots da API e amostra
manual) pela URL real e calcula as sete dimensões do enunciado. Grava o
resultado em `docs/metricas_qualidade.json`; a análise em prosa fica para
`docs/avaliacao_qualidade.md`.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from g1_scraper.config import RAIZ
from g1_scraper.dedup import chave
from g1_scraper.parser import eh_anuncio, extrair_hits, extrair_url_real, hit_para_resultado

FUSO = "America/Sao_Paulo"
DOMINIOS_ESPERADOS = {"g1.globo.com", "globoplay.globo.com"}
DIR_SAIDA = RAIZ / "data" / "output"
DIR_REFERENCIA = RAIZ / "data" / "reference"
DIR_BASELINE = RAIZ / "data" / "baseline"
DIR_DOCS = RAIZ / "docs"


# --- carregamento ---


def carregar_ultima_base() -> tuple[list[dict[str, str]], Path]:
    """Lê o CSV mais recente de `data/output/`."""
    csvs = sorted(DIR_SAIDA.glob("g1_lgpd_*.csv"))
    if not csvs:
        raise SystemExit("nenhuma base em data/output/ — rode a coleta final primeiro")
    caminho = csvs[-1]
    with caminho.open(encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo)), caminho


def carregar_manifesto(caminho_base: Path) -> dict[str, Any]:
    """Lê o manifesto correspondente à base carregada (mesmo carimbo de tempo)."""
    carimbo = caminho_base.stem.split("_")[-1]
    caminho = DIR_SAIDA / f"manifesto_{carimbo}.json"
    return json.loads(caminho.read_text(encoding="utf-8"))


def carregar_referencia_snapshots() -> tuple[list, list[str], str]:
    """Lê os snapshots da API (16/09). Devolve (registros sem anúncio, urls de
    anúncio, instante da coleta da referência)."""
    registros = []
    urls_anuncio = []
    coletado_em_ref = None
    for inicio in (0, 10, 20):
        caminho = DIR_REFERENCIA / f"snapshot_from_{inicio}.json"
        envelope = json.loads(caminho.read_text(encoding="utf-8"))
        coletado_em_ref = envelope["coletado_em"]
        for indice, hit in enumerate(extrair_hits(envelope["resposta"]), start=1):
            if eh_anuncio(hit):
                urls_anuncio.append(extrair_url_real(hit.get("_source", {}).get("url")))
                continue
            registros.append(
                hit_para_resultado(hit, inicio // 10, indice, coletado_em_ref, FUSO)
            )
    return registros, urls_anuncio, coletado_em_ref


def carregar_amostra_manual() -> tuple[list[dict[str, str]], list[str]]:
    """Lê a amostra manual (16/09). Devolve (linhas sem anúncio, urls de anúncio)."""
    caminho = DIR_REFERENCIA / "amostra_manual.csv"
    with caminho.open(encoding="utf-8") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    sem_anuncio = [linha for linha in linhas if linha["eh_anuncio"] == "nao"]
    urls_anuncio = [linha["url"] for linha in linhas if linha["eh_anuncio"] == "sim"]
    return sem_anuncio, urls_anuncio


# --- dimensões ---


def calcular_precisao(indice_base: dict[str, dict], urls_referencia: list[str]) -> dict:
    """Proporção de itens da referência (sem anúncio) presentes na base final."""
    achados = [u for u in urls_referencia if chave(u) in indice_base]
    total = len(urls_referencia)
    return {
        "encontrados": len(achados),
        "total_referencia": total,
        "proporcao": len(achados) / total if total else None,
        "faltantes": [u for u in urls_referencia if chave(u) not in indice_base],
    }


def calcular_acuracia(indice_base: dict[str, dict], referencia: list) -> dict:
    """Correspondência exata de titulo, resumo e data_atualizacao nos pareados."""
    campos = ("titulo", "resumo", "data_atualizacao")
    pareados = [r for r in referencia if chave(r.url) in indice_base]
    divergencias: dict[str, list[str]] = {c: [] for c in campos}
    for r in pareados:
        atual = indice_base[chave(r.url)]
        for campo in campos:
            if (getattr(r, campo) or "") != (atual[campo] or ""):
                divergencias[campo].append(r.url)
    total = len(pareados)
    return {
        "pareados": total,
        "por_campo": {
            campo: {
                "iguais": total - len(divergencias[campo]),
                "total": total,
                "proporcao": (total - len(divergencias[campo])) / total if total else None,
                "divergentes": divergencias[campo],
            }
            for campo in campos
        },
    }


def calcular_unicidade(manifesto: dict) -> dict:
    """1 − proporção de duplicados por URL real, sobre os registros brutos."""
    m = manifesto["metricas"]
    brutos = m["registros_brutos"]
    duplicados = m["duplicados_descartados"]
    return {
        "registros_brutos": brutos,
        "duplicados_descartados": duplicados,
        "proporcao": 1 - (duplicados / brutos) if brutos else None,
    }


def calcular_completude(manifesto: dict) -> dict:
    """Proporção de campos não vazios, por campo, a partir do manifesto."""
    m = manifesto["metricas"]
    total = m["registros_na_base"]
    ausentes = m["campos_ausentes"]
    return {
        campo: {
            "ausentes": qtd,
            "total": total,
            "proporcao": (total - qtd) / total if total else None,
        }
        for campo, qtd in ausentes.items()
    }


def calcular_consistencia(base: list[dict[str, str]], size: int) -> dict:
    """Datas ISO válidas no fuso -03:00; URL absoluta do domínio esperado;
    `pagina` inteiro >= 0; `posicao` entre 1 e `size`."""
    checagens = {"data_publicacao": 0, "data_atualizacao": 0, "url": 0, "pagina": 0, "posicao": 0}
    for r in base:
        for campo in ("data_publicacao", "data_atualizacao"):
            valor = r[campo]
            if valor:
                try:
                    momento = datetime.fromisoformat(valor)
                    if momento.utcoffset() is not None and momento.utcoffset().total_seconds() == -3 * 3600:
                        checagens[campo] += 1
                except ValueError:
                    pass
            else:
                checagens[campo] += 1  # ausente não é inconsistente, é completude
        partes = urlsplit(r["url"])
        if partes.scheme == "https" and partes.netloc in DOMINIOS_ESPERADOS:
            checagens["url"] += 1
        if r["pagina"].isdigit() and int(r["pagina"]) >= 0:
            checagens["pagina"] += 1
        if r["posicao"].isdigit() and 1 <= int(r["posicao"]) <= size:
            checagens["posicao"] += 1
    total = len(base)
    return {
        campo: {"validos": qtd, "total": total, "proporcao": qtd / total if total else None}
        for campo, qtd in checagens.items()
    }


def calcular_atualidade(base: list[dict[str, str]], coletado_em_ref: str, coletado_em_base: str) -> dict:
    """Intervalo entre a referência e a coleta; distribuição das datas de publicação."""
    ref = datetime.fromisoformat(coletado_em_ref.replace("Z", "+00:00"))
    atual = datetime.fromisoformat(coletado_em_base)
    anos: dict[str, int] = {}
    idades_dias = []
    for r in base:
        if r["data_publicacao"]:
            momento = datetime.fromisoformat(r["data_publicacao"])
            anos[str(momento.year)] = anos.get(str(momento.year), 0) + 1
            idades_dias.append((atual - momento).days)
    return {
        "intervalo_referencia_coleta_horas": (atual - ref).total_seconds() / 3600,
        "distribuicao_por_ano": dict(sorted(anos.items())),
        "idade_media_dias": sum(idades_dias) / len(idades_dias) if idades_dias else None,
        "idade_min_dias": min(idades_dias) if idades_dias else None,
        "idade_max_dias": max(idades_dias) if idades_dias else None,
    }


def calcular_rastreabilidade(base: list[dict[str, str]], manifesto: dict) -> dict:
    """Proporção de registros com pagina, posicao e coletado_em preenchidos,
    e vínculo ao manifesto (commit registrado)."""
    completos = sum(
        1 for r in base if r["pagina"] != "" and r["posicao"] != "" and r["coletado_em"] != ""
    )
    total = len(base)
    return {
        "campos_preenchidos": completos,
        "total": total,
        "proporcao": completos / total if total else None,
        "commit_registrado": manifesto.get("commit") is not None,
    }


def calcular_vazamento_anuncios(indice_base: dict[str, dict], urls_anuncio: list[str]) -> dict:
    """Quantos itens marcados como anúncio na referência aparecem na base final."""
    vazados = [u for u in urls_anuncio if chave(u) in indice_base]
    return {"total_anuncios_referencia": len(urls_anuncio), "vazados": vazados, "quantidade": len(vazados)}


def teste_contagem(manifesto: dict) -> dict:
    """registros_brutos + anuncios_filtrados == hits.total.value, só se 0 falhas."""
    m = manifesto["metricas"]
    aplica = m["paginas_com_falha"] == 0
    soma = m["registros_brutos"] + m["anuncios_filtrados"]
    return {
        "aplica": aplica,
        "soma": soma,
        "total_declarado": m["total_declarado"],
        "bate": (soma == m["total_declarado"]) if aplica else None,
    }


# --- execução ---


def main() -> None:
    base, caminho_base = carregar_ultima_base()
    manifesto = carregar_manifesto(caminho_base)
    indice_base = {chave(r["url"]): r for r in base if chave(r["url"])}

    ref_snap, anuncios_snap, coletado_em_ref = carregar_referencia_snapshots()
    manual, anuncios_manual = carregar_amostra_manual()
    urls_manual = [linha["url"] for linha in manual]

    resultado = {
        "base_avaliada": caminho_base.name,
        "precisao_snapshots": calcular_precisao(indice_base, [r.url for r in ref_snap]),
        "precisao_amostra_manual": calcular_precisao(indice_base, urls_manual),
        "acuracia": calcular_acuracia(indice_base, ref_snap),
        "unicidade": calcular_unicidade(manifesto),
        "completude": calcular_completude(manifesto),
        "consistencia": calcular_consistencia(base, manifesto["parametros"]["size"]),
        "atualidade": calcular_atualidade(base, coletado_em_ref, manifesto["executado_em"]),
        "rastreabilidade": calcular_rastreabilidade(base, manifesto),
        "vazamento_anuncios": calcular_vazamento_anuncios(
            indice_base, anuncios_snap + anuncios_manual
        ),
        "teste_contagem": teste_contagem(manifesto),
    }

    DIR_DOCS.mkdir(parents=True, exist_ok=True)
    caminho_saida = DIR_DOCS / "metricas_qualidade.json"
    caminho_saida.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"métricas gravadas em {caminho_saida}")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()