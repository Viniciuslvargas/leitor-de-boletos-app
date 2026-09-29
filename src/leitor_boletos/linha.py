import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .bancos import nome_do_banco

BASE_ANTIGA = date(1997, 10, 7)
BASE_NOVA = date(2022, 5, 29)
LIMITE_DATA_INCOMUM = 365

LIDO_POR_LINHA = "linha"
LIDO_POR_CODIGO = "código de barras"

VALOR_EM_ABERTO = "valor em aberto"
SEM_VENCIMENTO = "sem vencimento"
CONSULTE_O_BOLETO = "consulte o boleto"
VALOR_DE_REFERENCIA = "valor de referência, consulte o boleto"
VALOR_E_VENCIMENTO_988 = "valor e vencimento: consulte o boleto"
MOEDA_NAO_SUPORTADA = "moeda não suportada"
DATA_INCOMUM = "data incomum, confira no boleto"
AVISO_CODIGO_DE_BARRAS = "lido pelo código de barras"
BANCO_NAO_IDENTIFICADO = "banco não identificado"
LINHA_INVALIDA = "linha inválida"

SEGMENTOS = {
    "1": "Prefeitura",
    "2": "Saneamento",
    "3": "Energia elétrica e gás",
    "4": "Telecomunicações",
    "5": "Órgão do governo",
    "6": "Carnê e demais empresas",
    "7": "Multa de trânsito",
    "9": "Uso exclusivo do banco",
}


@dataclass(frozen=True)
class Boleto:
    origem: str
    numero: str
    tipo: str | None
    lido_por: str
    valido: bool
    motivo: str | None
    banco: str | None
    valor: Decimal | None
    valor_texto: str
    vencimento: date | None
    vencimento_texto: str
    situacao: str
    avisos: tuple[str, ...]
    entra_no_total: bool


def mod10(numero: str) -> int:
    soma, peso = 0, 2
    for digito in reversed(numero):
        produto = int(digito) * peso
        soma += produto // 10 + produto % 10
        peso = 1 if peso == 2 else 2
    return (10 - soma % 10) % 10


def _soma_mod11(numero: str) -> int:
    soma, peso = 0, 2
    for digito in reversed(numero):
        soma += int(digito) * peso
        peso = 2 if peso == 9 else peso + 1
    return soma


def mod11_banco(numero: str) -> int:
    dv = 11 - _soma_mod11(numero) % 11
    return 1 if dv in (0, 1, 10, 11) else dv


def mod11_consumo(numero: str) -> int:
    resto = _soma_mod11(numero) % 11
    return 0 if resto in (0, 1) else 11 - resto


def _conta_do_consumo(identificador: str):
    if identificador in "67":
        return mod10
    if identificador in "89":
        return mod11_consumo
    return None


def limpar(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def codigo_para_linha(codigo: str) -> str:
    if codigo[0] == "8":
        conta = _conta_do_consumo(codigo[2])
        if conta is None:
            raise ValueError("3º dígito inválido")
        blocos = [codigo[i : i + 11] for i in range(0, 44, 11)]
        return "".join(bloco + str(conta(bloco)) for bloco in blocos)
    campo1 = codigo[0:4] + codigo[19:24]
    campo2 = codigo[24:34]
    campo3 = codigo[34:44]
    return (
        campo1 + str(mod10(campo1))
        + campo2 + str(mod10(campo2))
        + campo3 + str(mod10(campo3))
        + codigo[4]
        + codigo[5:19]
    )


def _linha_para_codigo(linha: str) -> str:
    if len(linha) == 48:
        return "".join(linha[i : i + 11] for i in range(0, 48, 12))
    return linha[0:4] + linha[32] + linha[33:47] + linha[4:9] + linha[10:20] + linha[21:31]


def formatar(numero: str) -> str:
    if len(numero) == 47:
        n = numero
        return f"{n[0:5]}.{n[5:10]} {n[10:15]}.{n[15:21]} {n[21:26]}.{n[26:32]} {n[32]} {n[33:47]}"
    if len(numero) == 48:
        return " ".join(f"{numero[i:i + 11]}-{numero[i + 11]}" for i in range(0, 48, 12))
    return numero


def formatar_reais(valor: Decimal) -> str:
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def escolher_vencimento(fator: int, hoje: date) -> tuple[date | None, bool]:
    if fator == 0:
        return None, False
    antiga = BASE_ANTIGA + timedelta(days=fator)
    nova = BASE_NOVA + timedelta(days=fator)
    escolhida = min(nova, antiga, key=lambda d: abs((d - hoje).days))
    return escolhida, abs((escolhida - hoje).days) > LIMITE_DATA_INCOMUM


def situacao(vencimento: date, hoje: date) -> str:
    dias = (vencimento - hoje).days
    if dias < 0:
        return "vencido"
    if dias == 0:
        return "vence hoje"
    if dias == 1:
        return "vence amanhã"
    return f"vence em {dias} dias"


def invalido(origem: str, numero: str, tipo: str | None, lido_por: str, motivo: str) -> Boleto:
    return Boleto(
        origem=origem, numero=numero, tipo=tipo, lido_por=lido_por, valido=False,
        motivo=motivo, banco=None, valor=None, valor_texto="—", vencimento=None,
        vencimento_texto="—", situacao=LINHA_INVALIDA, avisos=(motivo,), entra_no_total=False,
    )


def interpretar(numero: str, hoje: date, origem: str = "colada",
                lido_por: str = LIDO_POR_LINHA) -> Boleto:
    n = limpar(numero)

    if len(n) == 44:
        return _do_codigo_de_barras(n, hoje, origem)
    if len(n) == 47:
        return _boleto_de_banco(n, hoje, origem, lido_por)
    if len(n) == 48:
        if n[0] != "8":
            return invalido(origem, n, None, lido_por,
                             "linha de 48 números precisa começar com 8")
        return _conta_de_consumo(n, origem, lido_por)
    return invalido(origem, n, None, lido_por, "a linha precisa ter 44, 47 ou 48 números")


def _do_codigo_de_barras(codigo: str, hoje: date, origem: str) -> Boleto:
    if codigo[0] == "8":
        conta = _conta_do_consumo(codigo[2])
        if conta is None:
            return invalido(origem, codigo, "consumo", LIDO_POR_CODIGO,
                             "3º dígito inválido (deve ser 6, 7, 8 ou 9)")
        if conta(codigo[:3] + codigo[4:]) != int(codigo[3]):
            return invalido(origem, codigo, "consumo", LIDO_POR_CODIGO,
                             "dígito verificador geral não confere")
        return _conta_de_consumo(codigo_para_linha(codigo), origem, LIDO_POR_CODIGO)
    if mod11_banco(codigo[:4] + codigo[5:]) != int(codigo[4]):
        return invalido(origem, codigo, "banco", LIDO_POR_CODIGO,
                         "dígito verificador geral não confere")
    return _boleto_de_banco(codigo_para_linha(codigo), hoje, origem, LIDO_POR_CODIGO)


def _boleto_de_banco(linha: str, hoje: date, origem: str, lido_por: str) -> Boleto:
    for campo, (inicio, fim) in enumerate(((0, 9), (10, 20), (21, 31)), start=1):
        if mod10(linha[inicio:fim]) != int(linha[fim]):
            return invalido(origem, linha, "banco", lido_por, f"dígito do campo {campo} não confere")
    codigo = _linha_para_codigo(linha)
    if mod11_banco(codigo[:4] + codigo[5:]) != int(codigo[4]):
        return invalido(origem, linha, "banco", lido_por, "dígito verificador geral não confere")

    avisos = [AVISO_CODIGO_DE_BARRAS] if lido_por == LIDO_POR_CODIGO else []
    codigo_banco, moeda = linha[0:3], linha[3]
    fator, centavos = int(linha[33:37]), int(linha[37:47])

    if codigo_banco == "988":
        avisos.append(VALOR_E_VENCIMENTO_988)
        return Boleto(
            origem=origem, numero=linha, tipo="banco", lido_por=lido_por, valido=True,
            motivo=VALOR_E_VENCIMENTO_988, banco="Instituição sem número de banco (988)",
            valor=None, valor_texto=CONSULTE_O_BOLETO, vencimento=None,
            vencimento_texto=CONSULTE_O_BOLETO, situacao=CONSULTE_O_BOLETO,
            avisos=tuple(avisos), entra_no_total=False,
        )

    nome = nome_do_banco(codigo_banco)
    if nome is None:
        banco = codigo_banco
        avisos.append(BANCO_NAO_IDENTIFICADO)
    else:
        banco = f"{nome} ({codigo_banco})"

    motivo = None
    if moeda != "9":
        valor, valor_texto, motivo = None, MOEDA_NAO_SUPORTADA, MOEDA_NAO_SUPORTADA
    elif centavos == 0:
        valor, valor_texto, motivo = None, VALOR_EM_ABERTO, VALOR_EM_ABERTO
    else:
        valor = Decimal(centavos) / 100
        valor_texto = formatar_reais(valor)

    vencimento, incomum = escolher_vencimento(fator, hoje)
    if vencimento is None:
        vencimento_texto = situacao_texto = SEM_VENCIMENTO
    else:
        vencimento_texto = vencimento.strftime("%d/%m/%Y")
        situacao_texto = situacao(vencimento, hoje)
        if incomum:
            avisos.append(DATA_INCOMUM)

    return Boleto(
        origem=origem, numero=linha, tipo="banco", lido_por=lido_por, valido=True,
        motivo=motivo, banco=banco, valor=valor, valor_texto=valor_texto,
        vencimento=vencimento, vencimento_texto=vencimento_texto, situacao=situacao_texto,
        avisos=tuple(avisos), entra_no_total=valor is not None,
    )


def _conta_de_consumo(linha: str, origem: str, lido_por: str) -> Boleto:
    identificador = linha[2]
    conta = _conta_do_consumo(identificador)
    if conta is None:
        return invalido(origem, linha, "consumo", lido_por,
                         "3º dígito inválido (deve ser 6, 7, 8 ou 9)")
    for bloco in range(4):
        inicio = bloco * 12
        if conta(linha[inicio : inicio + 11]) != int(linha[inicio + 11]):
            return invalido(origem, linha, "consumo", lido_por,
                             f"dígito do bloco {bloco + 1} não confere")
    codigo = _linha_para_codigo(linha)
    if conta(codigo[:3] + codigo[4:]) != int(codigo[3]):
        return invalido(origem, linha, "consumo", lido_por, "dígito verificador geral não confere")

    avisos = [AVISO_CODIGO_DE_BARRAS] if lido_por == LIDO_POR_CODIGO else []
    segmento = linha[1]
    banco = SEGMENTOS.get(segmento, f"Segmento {segmento}")

    motivo = None
    if identificador in "79":
        valor, valor_texto, motivo = None, VALOR_DE_REFERENCIA, VALOR_DE_REFERENCIA
        avisos.append(VALOR_DE_REFERENCIA)
    else:
        centavos = int(codigo[4:15])
        if centavos == 0:
            valor, valor_texto, motivo = None, VALOR_EM_ABERTO, VALOR_EM_ABERTO
        else:
            valor = Decimal(centavos) / 100
            valor_texto = formatar_reais(valor)

    return Boleto(
        origem=origem, numero=linha, tipo="consumo", lido_por=lido_por, valido=True,
        motivo=motivo, banco=banco, valor=valor, valor_texto=valor_texto, vencimento=None,
        vencimento_texto=CONSULTE_O_BOLETO, situacao=CONSULTE_O_BOLETO,
        avisos=tuple(avisos), entra_no_total=valor is not None,
    )
