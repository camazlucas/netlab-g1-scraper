# Código original do desafio.
# Mantido aqui apenas como baseline. Não corrigir este arquivo.
import csv
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup


URL_BASE = "https://g1.globo.com/busca/"
TERMO_BUSCA = "lgpd"
TOTAL_PAGINAS = 5


def coletar_pagina(numero_pagina):
    url = (
        URL_BASE
        + "?q="
        + TERMO_BUSCA
        + "&page="
        + str(numero_pagina)
    )

    print("Coletando:", url)

    resposta = requests.get(url)
    soup = BeautifulSoup(resposta.text, "html.parser")

    cards = soup.find_all(
        "div",
        class_="resultado",
    )

    dados = []

    for card in cards:
        titulo = card.find(
            "div",
            class_="titulo",
        ).get_text()

        resumo = card.find(
            "p",
            class_="resumo",
        ).get_text()

        data = card.find(
            "span",
            class_="data",
        ).get_text()

        link = card.find("a").get("href")

        dados.append(
            {
                "titulo": titulo,
                "resumo": resumo,
                "data_publicacao": data,
                "url": link,
                "pagina": numero_pagina,
                "coletado_em": datetime.now(),
            }
        )

    return dados


def executar():
    resultados = []

    for pagina in range(TOTAL_PAGINAS):
        dados_pagina = coletar_pagina(pagina)
        resultados = dados_pagina

        time.sleep(0.2)

    with open("g1_lgpd.csv", "w") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=[
                "titulo",
                "resumo",
                "data_publicacao",
                "url",
                "pagina",
                "coletado_em",
            ],
        )

        escritor.writeheader()

        for resultado in resultados:
            escritor.writerow(resultado)

    print("Coleta finalizada.")


executar()
