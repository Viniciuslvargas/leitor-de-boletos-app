from collections import Counter
from dataclasses import dataclass, replace
from decimal import Decimal

from .linha import Boleto

DUPLICADO = "duplicado"
INVALIDO = "inválido"


@dataclass
class Tabela:
    linhas: list[Boleto]
    total: Decimal
    fora_do_total: dict[str, int]


def montar(boletos: list[Boleto]) -> Tabela:
    linhas = []
    vistos: set[str] = set()
    for boleto in boletos:
        if boleto.valido and boleto.numero in vistos:
            boleto = replace(boleto, avisos=boleto.avisos + (DUPLICADO,),
                             entra_no_total=False, motivo=DUPLICADO)
        elif boleto.valido:
            vistos.add(boleto.numero)
        linhas.append(boleto)

    total = sum(
        (b.valor for b in linhas if b.valido and b.entra_no_total and b.valor is not None),
        Decimal("0"),
    )
    fora = Counter(
        INVALIDO if not b.valido else (b.motivo or "sem valor")
        for b in linhas if not b.entra_no_total
    )
    return Tabela(linhas=linhas, total=total, fora_do_total=dict(fora))
