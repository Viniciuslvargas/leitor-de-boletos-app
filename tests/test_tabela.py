from datetime import date
from decimal import Decimal
from pathlib import Path

from leitor_boletos import linha as L
from leitor_boletos.pdf import ler_pdf
from leitor_boletos.tabela import DUPLICADO, INVALIDO, montar

HOJE = date(2026, 9, 29)
EXEMPLOS = Path(__file__).resolve().parent.parent / "exemplos"

CAIXA = "10490055057722213334877777777713432420000032112"
BRADESCO = "23790031024003177200328009527905710010000000000"


def test_armadilha_08_duplicado():
    primeiro = L.interpretar(CAIXA, HOJE, "a.pdf")
    segundo = L.interpretar(CAIXA, HOJE, "b.pdf")
    tabela = montar([primeiro, segundo])
    assert tabela.linhas[0].entra_no_total
    assert not tabela.linhas[1].entra_no_total
    assert DUPLICADO in tabela.linhas[1].avisos
    assert tabela.total == Decimal("321.12")


def test_total_e_fora_do_total():
    invalido = L.interpretar(CAIXA[:-1] + "3", HOJE)
    tabela = montar([
        L.interpretar(CAIXA, HOJE),
        L.interpretar(BRADESCO, HOJE),
        invalido,
        L.interpretar(CAIXA, HOJE),
    ])
    assert tabela.total == Decimal("321.12")
    assert tabela.fora_do_total == {L.VALOR_EM_ABERTO: 1, INVALIDO: 1, DUPLICADO: 1}


def test_carne_uma_linha_por_boleto():
    boletos = ler_pdf(EXEMPLOS / "13-carne.pdf", HOJE)
    assert len(boletos) == 2
    assert boletos[0].numero != boletos[1].numero
    assert montar(boletos).total == Decimal("400.00")


def test_tabela_vazia():
    tabela = montar([])
    assert tabela.linhas == [] and tabela.total == Decimal("0") and tabela.fora_do_total == {}
