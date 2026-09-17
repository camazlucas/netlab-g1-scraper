"""Modelo do registro coletado: fonte única dos campos e das colunas de saída."""

from dataclasses import dataclass, fields


@dataclass(frozen=True, slots=True)
class Resultado:
    """Um resultado da busca do G1, já normalizado e pronto para gravação.

    A ordem de declaração dos atributos define a ordem das colunas no CSV.
    """

    titulo: str | None
    url: str | None
    resumo: str | None
    data_publicacao: str | None
    data_atualizacao: str | None
    pagina: int
    posicao: int
    coletado_em: str


def colunas() -> tuple[str, ...]:
    """Devolve os nomes das colunas de saída, na ordem declarada em `Resultado`."""
    return tuple(campo.name for campo in fields(Resultado))
