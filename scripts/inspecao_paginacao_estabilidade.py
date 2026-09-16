"""Etapa 4, questão 4: `total` e ordem são estáveis entre requisições repetidas?"""
import json
import time
from pathlib import Path

from inspecao_paginacao import buscar
from inspecao_paginacao_size import urls

SAIDA = Path("data/baseline/api")
REPETICOES = 5
TAMANHO = 50


def main():
    salvo = json.loads((SAIDA / "paginacao_from_0.json").read_text(encoding="utf-8"))
    primeira = None
    for i in range(REPETICOES):
        dados = buscar(0, TAMANHO)
        (SAIDA / f"estabilidade_rep_{i}.json").write_text(
            json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        hits = dados[0]["result"]["hits"]
        atual = urls(dados)
        if primeira is None:
            primeira = atual
        print(f"rep {i}: total={hits['total']['value']}, max_score={hits.get('max_score')}, "
              f"mesma ordem={atual == primeira}, mesmo conjunto={set(atual) == set(primeira)}")
        time.sleep(2)

    print(f"10 primeiros iguais ao arquivo da questão 1 (ordem): {primeira[:10] == urls(salvo)}")


if __name__ == "__main__":
    main()