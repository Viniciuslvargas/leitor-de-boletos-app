from datetime import date
from decimal import Decimal
from pathlib import Path

import pdfplumber

from leitor_boletos import linha as L
from leitor_boletos.pdf import NAO_ABRE, SEM_LINHA, achar_boletos, ler_pdf
from leitor_boletos.tabela import montar

HOJE = date(2026, 9, 29)
EXEMPLOS = Path(__file__).resolve().parent.parent / "exemplos"


def ler_gabarito() -> list[dict]:
    linhas = []
    for texto in (EXEMPLOS / "LEIA-ME.md").read_text(encoding="utf-8").splitlines():
        if not texto.startswith("| `"):
            continue
        celulas = [c.strip() for c in texto.strip("|").split("|")]
        arquivo, _, banco, valor, vencimento, situacao, avisos, entra = celulas
        linhas.append({
            "arquivo": arquivo.strip("`"), "banco": banco, "valor": valor,
            "vencimento": vencimento, "situacao": situacao,
            "avisos": [] if avisos == "-" else avisos.split("; "), "entra": entra == "sim",
        })
    return linhas


def test_armadilha_06_linha_quebrada():
    boletos = ler_pdf(EXEMPLOS / "02-linha-quebrada.pdf", HOJE)
    assert len(boletos) == 1 and boletos[0].valido
    assert boletos[0].valor == Decimal("1249.90")


def test_armadilha_07_numeros_vizinhos():
    boletos = ler_pdf(EXEMPLOS / "03-numeros-vizinhos.pdf", HOJE)
    assert len(boletos) == 1 and boletos[0].valido
    assert boletos[0].banco == "Banco do Brasil S.A. (001)"
    assert boletos[0].valor == Decimal("89.75")


def test_ex01_pdf_sem_texto():
    boletos = ler_pdf(EXEMPLOS / "12-so-imagem.pdf", HOJE)
    assert len(boletos) == 1
    assert not boletos[0].valido and boletos[0].motivo == SEM_LINHA


def test_ex03_pdf_corrompido(tmp_path):
    falso = tmp_path / "quebrado.pdf"
    falso.write_bytes(b"isto nao e um PDF")
    boletos = ler_pdf(falso, HOJE)
    assert len(boletos) == 1
    assert not boletos[0].valido and boletos[0].motivo == NAO_ABRE


def test_codigo_de_barras_so_quando_nao_ha_linha():
    boletos = ler_pdf(EXEMPLOS / "10-so-codigo-de-barras.pdf", HOJE)
    assert len(boletos) == 1 and boletos[0].lido_por == L.LIDO_POR_CODIGO


def test_linha_tem_prioridade_sobre_codigo_de_barras():
    linha = "10490055057722213334877777777713432420000032112"
    sem_dv = "3419" + "1234567890123456789012345678901234567890"[:39]
    falso = sem_dv[:4] + str(L.mod11_banco(sem_dv)) + sem_dv[4:]
    assert L.interpretar(falso, HOJE).valido
    texto = "\n".join([f"Linha: {linha}", f"Outro numero: {falso}"])
    boletos = achar_boletos(texto, HOJE, "x.pdf")
    assert [b.numero for b in boletos] == [linha]


def test_texto_codificado_em_cid(monkeypatch, tmp_path):
    linha = "10490.05505 77222.133348 77777.777713 4 32420000032112"
    codificado = "".join(f"(cid:{ord(c)})" for c in f"Linha: {linha}")
    monkeypatch.setattr(pdfplumber, "open", _pdf_falso(codificado))
    boletos = ler_pdf(tmp_path / "cid.pdf", HOJE)
    assert len(boletos) == 1 and boletos[0].valido
    assert boletos[0].valor == Decimal("321.12")


def _pdf_falso(texto):
    class Pagina:
        def extract_text(self):
            return texto

    class Pdf:
        pages = [Pagina()]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    return lambda _caminho: Pdf()


def test_digito_errado_vira_linha_invalida():
    boletos = ler_pdf(EXEMPLOS / "11-digito-errado.pdf", HOJE)
    assert len(boletos) == 1
    assert boletos[0].motivo == "dígito do campo 2 não confere"


def test_todos_os_exemplos():
    gabarito = ler_gabarito()
    arquivos = sorted(EXEMPLOS.glob("*.pdf"))
    assert len(arquivos) == 13

    boletos = [b for arquivo in arquivos for b in ler_pdf(arquivo, HOJE)]
    tabela = montar(boletos)

    assert len(tabela.linhas) == len(gabarito)
    for boleto, esperado in zip(tabela.linhas, gabarito):
        obtido = {
            "arquivo": boleto.origem, "banco": boleto.banco or "—", "valor": boleto.valor_texto,
            "vencimento": boleto.vencimento_texto, "situacao": boleto.situacao,
            "avisos": list(boleto.avisos), "entra": boleto.entra_no_total,
        }
        assert obtido == esperado, esperado["arquivo"]
    assert tabela.total == Decimal("2457.00")
