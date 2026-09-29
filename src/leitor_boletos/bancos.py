import csv
from functools import cache
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent / "dados" / "bancos.csv"


@cache
def _tabela() -> dict[str, str]:
    with open(ARQUIVO, encoding="utf-8", newline="") as arquivo:
        return {linha["codigo"]: linha["nome"] for linha in csv.DictReader(arquivo, delimiter=";")}


def nome_do_banco(codigo: str) -> str | None:
    return _tabela().get(codigo)
