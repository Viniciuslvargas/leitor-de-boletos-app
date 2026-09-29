import csv
import io
import urllib.request
from datetime import date
from pathlib import Path

URL = "https://www.bcb.gov.br/content/estabilidadefinanceira/str1/ParticipantesSTR.csv"
DADOS = Path(__file__).resolve().parent.parent / "src" / "leitor_boletos" / "dados"

LICENCA = """Lista de bancos (bancos.csv)

Fonte: Banco Central do Brasil - Lista de Participantes do STR (dados abertos)
{url}
Baixada em: {data}
Colunas usadas: Numero_Codigo -> codigo; Nome_Extenso -> nome.

Esta base de dados e disponibilizada sob a Open Database License (ODbL) v1.0:
https://opendatacommons.org/licenses/odbl/1-0/
A base adaptada (bancos.csv) segue sob a mesma licenca. O codigo do programa segue sob a licenca MIT.
"""


def baixar() -> str:
    pedido = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(pedido, timeout=30) as resposta:
        return resposta.read().decode("utf-8-sig")


def converter(texto: str) -> list[tuple[str, str]]:
    bancos = {}
    for linha in csv.DictReader(io.StringIO(texto)):
        codigo = linha["Número_Código"].strip()
        nome = linha["Nome_Extenso"].strip() or linha["Nome_Reduzido"].strip()
        if codigo.isdigit() and nome:
            bancos[codigo.zfill(3)] = nome
    return sorted(bancos.items())


def main() -> None:
    bancos = converter(baixar())
    DADOS.mkdir(parents=True, exist_ok=True)
    with open(DADOS / "bancos.csv", "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(["codigo", "nome"])
        escritor.writerows(bancos)
    (DADOS / "LICENCA-bancos.txt").write_text(
        LICENCA.format(url=URL, data=date.today().strftime("%d/%m/%Y")), encoding="utf-8"
    )
    print(f"{len(bancos)} bancos gravados em {DADOS / 'bancos.csv'}")


if __name__ == "__main__":
    main()
