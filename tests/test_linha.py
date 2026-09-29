from datetime import date
from decimal import Decimal

import pytest

from leitor_boletos import linha as L

HOJE = date(2026, 9, 29)


def montar_banco(banco="341", moeda="9", fator=1667, centavos=12345, livre="1" * 25):
    sem_dv = f"{banco}{moeda}{fator:04d}{centavos:010d}{livre}"
    dv = L.mod11_banco(sem_dv)
    codigo = sem_dv[:4] + str(dv) + sem_dv[4:]
    return L.codigo_para_linha(codigo), codigo


def montar_consumo(segmento="3", identificador="8", centavos=15990, resto="1" * 29):
    sem_dv = f"8{segmento}{identificador}{centavos:011d}{resto}"
    conta = L.mod10 if identificador in "67" else L.mod11_consumo
    codigo = sem_dv[:3] + str(conta(sem_dv)) + sem_dv[3:]
    return L.codigo_para_linha(codigo), codigo


def trocar_digito(numero: str, posicao: int) -> str:
    novo = str((int(numero[posicao]) + 1) % 10)
    return numero[:posicao] + novo + numero[posicao + 1 :]


def test_exemplos_oficiais_modulo_10_e_11_febraban():
    assert L.mod10("01230067896") == 3
    assert L.mod11_consumo("01230067896") == 0


def test_exemplos_oficiais_digito_geral_febraban():
    codigo_p15 = "82210000215048200974123220154098290108605940"
    assert L.mod10(codigo_p15[:3] + codigo_p15[4:]) == 1
    codigo_p17 = "82200000215048200974123220154098290108605940"
    assert L.mod11_consumo(codigo_p17[:3] + codigo_p17[4:]) == 0


def test_exemplos_oficiais_codigo_de_barras_banpara():
    codigo = "03794819000000199900000999100650000000000402"
    assert L.mod11_banco(codigo[:4] + codigo[5:]) == 4
    boleto = L.interpretar(codigo, HOJE)
    assert boleto.valido
    assert boleto.valor == Decimal("199.90")
    assert boleto.vencimento == date(2020, 3, 10)
    assert L.AVISO_CODIGO_DE_BARRAS in boleto.avisos
    assert L.DATA_INCOMUM in boleto.avisos


def test_exemplos_oficiais_linha_da_caixa():
    boleto = L.interpretar("10490.05505 77222.133348 77777.777713 4 32420000032112", HOJE)
    assert boleto.valido
    assert boleto.banco == "CAIXA ECONOMICA FEDERAL (104)"
    assert boleto.valor == Decimal("321.12")
    assert boleto.valor_texto == "R$ 321,12"
    assert boleto.vencimento == date(2031, 4, 14)
    assert L.DATA_INCOMUM in boleto.avisos


def test_exemplos_oficiais_linha_do_bradesco():
    boleto = L.interpretar("23790031024003177200328009527905710010000000000", HOJE)
    assert boleto.valido
    assert boleto.valor is None
    assert boleto.valor_texto == L.VALOR_EM_ABERTO


def test_exemplos_oficiais_tabela_de_fatores():
    assert L.BASE_ANTIGA.toordinal() + 1000 == date(2000, 7, 3).toordinal()
    assert L.BASE_ANTIGA.toordinal() + 9999 == date(2025, 2, 21).toordinal()
    assert L.BASE_NOVA.toordinal() + 1000 == date(2025, 2, 22).toordinal()
    assert L.BASE_NOVA.toordinal() + 9999 == date(2049, 10, 13).toordinal()


def test_armadilha_01_fator_ciclo_novo():
    linha, _ = montar_banco(fator=1667)
    boleto = L.interpretar(linha, HOJE)
    assert boleto.vencimento == date(2026, 12, 21)
    assert boleto.situacao == "vence em 83 dias"
    assert L.DATA_INCOMUM not in boleto.avisos


def test_armadilha_01_aviso_data_incomum():
    linha, _ = montar_banco(fator=9000)
    boleto = L.interpretar(linha, HOJE)
    assert boleto.vencimento == date(2022, 5, 29)
    assert boleto.situacao == "vencido"
    assert L.DATA_INCOMUM in boleto.avisos


def test_armadilha_02_fator_zero():
    linha, _ = montar_banco(fator=0)
    boleto = L.interpretar(linha, HOJE)
    assert boleto.vencimento is None
    assert boleto.vencimento_texto == L.SEM_VENCIMENTO
    assert boleto.situacao == L.SEM_VENCIMENTO
    assert boleto.entra_no_total


def test_armadilha_03_valor_zero():
    linha, _ = montar_banco(centavos=0)
    boleto = L.interpretar(linha, HOJE)
    assert boleto.valor is None
    assert boleto.valor_texto == L.VALOR_EM_ABERTO
    assert not boleto.entra_no_total


def test_armadilha_04_consumo_sem_vencimento():
    linha, _ = montar_consumo(segmento="3", identificador="8", centavos=15990)
    boleto = L.interpretar(linha, HOJE)
    assert boleto.valido and boleto.tipo == "consumo"
    assert boleto.banco == "Energia elétrica e gás"
    assert boleto.valor == Decimal("159.90")
    assert boleto.vencimento is None
    assert boleto.vencimento_texto == L.CONSULTE_O_BOLETO
    assert boleto.entra_no_total


@pytest.mark.parametrize("posicao, motivo", [
    (2, "dígito do campo 1 não confere"),
    (14, "dígito do campo 2 não confere"),
    (25, "dígito do campo 3 não confere"),
    (32, "dígito verificador geral não confere"),
    (40, "dígito verificador geral não confere"),
])
def test_armadilha_05_digito_errado_banco(posicao, motivo):
    linha, _ = montar_banco()
    boleto = L.interpretar(trocar_digito(linha, posicao), HOJE)
    assert not boleto.valido
    assert boleto.motivo == motivo
    assert boleto.situacao == L.LINHA_INVALIDA
    assert not boleto.entra_no_total


@pytest.mark.parametrize("posicao, motivo", [
    (5, "dígito do bloco 1 não confere"),
    (30, "dígito do bloco 3 não confere"),
])
def test_armadilha_05_digito_errado_consumo(posicao, motivo):
    linha, _ = montar_consumo()
    boleto = L.interpretar(trocar_digito(linha, posicao), HOJE)
    assert not boleto.valido
    assert boleto.motivo == motivo


@pytest.mark.parametrize("identificador", ["7", "9"])
def test_armadilha_09_valor_referencia(identificador):
    linha, _ = montar_consumo(identificador=identificador, centavos=12345)
    boleto = L.interpretar(linha, HOJE)
    assert boleto.valido
    assert boleto.valor is None
    assert boleto.valor_texto == L.VALOR_DE_REFERENCIA
    assert not boleto.entra_no_total


def test_armadilha_10_codigo_988():
    linha, _ = montar_banco(banco="988", fator=1667, centavos=12345)
    boleto = L.interpretar(linha, HOJE)
    assert boleto.valido
    assert boleto.valor is None and boleto.vencimento is None
    assert boleto.valor_texto == L.CONSULTE_O_BOLETO
    assert L.VALOR_E_VENCIMENTO_988 in boleto.avisos
    assert not boleto.entra_no_total


def test_codigo_de_barras_44_banco_e_consumo():
    linha, codigo = montar_banco()
    por_codigo = L.interpretar(codigo, HOJE)
    assert por_codigo.numero == linha
    assert por_codigo.lido_por == L.LIDO_POR_CODIGO
    assert L.AVISO_CODIGO_DE_BARRAS in por_codigo.avisos
    assert por_codigo.valor == L.interpretar(linha, HOJE).valor

    linha_c, codigo_c = montar_consumo()
    assert L.interpretar(codigo_c, HOJE).numero == linha_c


def test_codigo_de_barras_44_com_digito_errado():
    _, codigo = montar_banco()
    boleto = L.interpretar(trocar_digito(codigo, 20), HOJE)
    assert not boleto.valido
    assert boleto.motivo == "dígito verificador geral não confere"


def test_moeda_nao_suportada():
    linha, _ = montar_banco(moeda="0")
    boleto = L.interpretar(linha, HOJE)
    assert boleto.valido
    assert boleto.valor_texto == L.MOEDA_NAO_SUPORTADA
    assert not boleto.entra_no_total


def test_banco_nao_identificado():
    linha, _ = montar_banco(banco="999")
    boleto = L.interpretar(linha, HOJE)
    assert boleto.banco == "999"
    assert L.BANCO_NAO_IDENTIFICADO in boleto.avisos
    assert boleto.entra_no_total


def test_nome_do_banco():
    linha, _ = montar_banco(banco="001")
    assert L.interpretar(linha, HOJE).banco == "Banco do Brasil S.A. (001)"


@pytest.mark.parametrize("dias, esperado", [
    (-3, "vencido"), (0, "vence hoje"), (1, "vence amanhã"), (10, "vence em 10 dias"),
])
def test_situacao(dias, esperado):
    assert L.situacao(date.fromordinal(HOJE.toordinal() + dias), HOJE) == esperado


def test_linha_com_pontos_espacos_e_quebra():
    linha, _ = montar_banco()
    sujo = L.formatar(linha).replace(" ", "\n  ", 2)
    assert L.interpretar(sujo, HOJE).numero == linha


@pytest.mark.parametrize("numero, motivo", [
    ("1234", "a linha precisa ter 44, 47 ou 48 números"),
    ("1" * 48, "linha de 48 números precisa começar com 8"),
])
def test_tamanho_invalido(numero, motivo):
    boleto = L.interpretar(numero, HOJE)
    assert not boleto.valido and boleto.motivo == motivo


def test_formatar():
    assert L.formatar("10490055057722213334877777777713432420000032112") == (
        "10490.05505 77222.133348 77777.777713 4 32420000032112"
    )
    assert L.formatar_reais(Decimal("1234.5")) == "R$ 1.234,50"
