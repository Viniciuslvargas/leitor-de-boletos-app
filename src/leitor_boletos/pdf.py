import re
from datetime import date
from pathlib import Path

import pdfplumber

from . import linha as L

SEM_LINHA = "não encontrei a linha, cole manualmente"
NAO_ABRE = "não consegui abrir este PDF"

TRECHO_NUMERICO = re.compile(r"\d[\d.\s-]*\d")


CODIGO_CID = re.compile(r"\(cid:(\d+)\)")


def decodificar_cid(texto: str) -> str:
    def trocar(m: re.Match) -> str:
        codigo = int(m.group(1))
        return chr(codigo) if 32 <= codigo <= 255 else ""
    return CODIGO_CID.sub(trocar, texto)


def extrair_texto(caminho: Path) -> str:
    with pdfplumber.open(caminho) as pdf:
        texto = "\n".join(pagina.extract_text() or "" for pagina in pdf.pages)
    return decodificar_cid(texto) if "(cid:" in texto else texto


def _janelas(digitos: str) -> list[str]:
    if len(digitos) in (47, 48):
        return [digitos]
    if len(digitos) > 48:
        return [digitos[i : i + n] for n in (47, 48) for i in range(len(digitos) - n + 1)]
    return []


def ler_pdf(caminho: Path | str, hoje: date) -> list[L.Boleto]:
    caminho = Path(caminho)
    origem = caminho.name

    try:
        texto = extrair_texto(caminho)
    except Exception:
        return [L.invalido(origem, "", None, L.LIDO_POR_LINHA, NAO_ABRE)]
    if not texto.strip():
        return [L.invalido(origem, "", None, L.LIDO_POR_LINHA, SEM_LINHA)]
    return achar_boletos(texto, hoje, origem)


def achar_boletos(texto: str, hoje: date, origem: str) -> list[L.Boleto]:
    validos: list[L.Boleto] = []
    invalidos: list[L.Boleto] = []
    codigos_de_barras: list[str] = []
    vistos: set[str] = set()

    for trecho in TRECHO_NUMERICO.finditer(texto):
        digitos = L.limpar(trecho.group())
        if len(digitos) == 44:
            codigos_de_barras.append(digitos)
        for candidato in _janelas(digitos):
            if len(candidato) == 48 and candidato[0] != "8":
                continue
            boleto = L.interpretar(candidato, hoje, origem)
            if boleto.valido:
                if boleto.numero not in vistos:
                    vistos.add(boleto.numero)
                    validos.append(boleto)
            elif candidato == digitos:
                invalidos.append(boleto)

    if validos:
        return validos

    for codigo in codigos_de_barras:
        boleto = L.interpretar(codigo, hoje, origem)
        if boleto.valido and boleto.numero not in vistos:
            vistos.add(boleto.numero)
            validos.append(boleto)
    if validos:
        return validos

    if invalidos:
        return [invalidos[0]]
    return [L.invalido(origem, "", None, L.LIDO_POR_LINHA, SEM_LINHA)]
