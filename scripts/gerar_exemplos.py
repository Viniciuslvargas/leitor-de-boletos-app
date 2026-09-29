import io
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from leitor_boletos import linha as L

SAIDA = RAIZ / "exemplos"
HOJE = date(2026, 9, 29)
CRIACAO = datetime(2026, 9, 29, tzinfo=timezone.utc)
SELO = "EXEMPLO FICTÍCIO - NÃO É UM BOLETO REAL"


def fator_de(vencimento: date | None) -> int:
    return 0 if vencimento is None else (vencimento - L.BASE_NOVA).days


def codigo_banco(banco: str, vencimento: date | None, centavos: int, livre: str,
                 moeda: str = "9") -> str:
    assert len(livre) == 25, livre
    sem_dv = f"{banco}{moeda}{fator_de(vencimento):04d}{centavos:010d}{livre}"
    return sem_dv[:4] + str(L.mod11_banco(sem_dv)) + sem_dv[4:]


def codigo_consumo(segmento: str, identificador: str, centavos: int, resto: str) -> str:
    assert len(resto) == 29, resto
    sem_dv = f"8{segmento}{identificador}{centavos:011d}{resto}"
    conta = L.mod10 if identificador in "67" else L.mod11_consumo
    return sem_dv[:3] + str(conta(sem_dv)) + sem_dv[3:]


def trocar_digito(numero: str, posicao: int) -> str:
    return numero[:posicao] + str((int(numero[posicao]) + 1) % 10) + numero[posicao + 1:]


@dataclass
class Boleto:
    impresso: str
    banco: str
    valor: str
    vencimento: str
    situacao: str
    avisos: list[str] = field(default_factory=list)
    entra_no_total: bool = True
    valido: bool = True


@dataclass
class Exemplo:
    arquivo: str
    cobre: str
    beneficiario_banco: str
    boletos: list[Boleto]
    valor_impresso: str
    vencimento_impresso: str
    extra: list[str] = field(default_factory=list)
    quebrar_linha: bool = False
    so_imagem: bool = False
    copia_de: str | None = None
    esperado_arquivo: str | None = None


def data_txt(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def situacao(d: date) -> str:
    dias = (d - HOJE).days
    return "vencido" if dias < 0 else "vence hoje" if dias == 0 else (
        "vence amanhã" if dias == 1 else f"vence em {dias} dias")


def exemplos() -> list[Exemplo]:
    lista = []

    def banco_simples(arquivo, cobre, banco, nome, venc, centavos, livre, **kw):
        cod = codigo_banco(banco, venc, centavos, livre)
        lin = L.formatar(L.codigo_para_linha(cod))
        valor = L.formatar_reais(Decimal(centavos) / 100) if centavos else L.VALOR_EM_ABERTO
        b = Boleto(
            impresso=lin, banco=f"{nome} ({banco})", valor=valor,
            vencimento=data_txt(venc) if venc else L.SEM_VENCIMENTO,
            situacao=situacao(venc) if venc else L.SEM_VENCIMENTO,
            entra_no_total=bool(centavos),
        )
        return Exemplo(arquivo, cobre, nome, [b], valor if centavos else "R$ 0,00",
                       data_txt(venc) if venc else "Contra-apresentação", **kw)

    lista.append(banco_simples(
        "01-banco-normal.pdf", "caso comum; vencimento no ciclo novo do fator (armadilha 1)",
        "341", "ITAÚ UNIBANCO S.A.", date(2026, 10, 15), 35000, "1090000000000001000000001"))
    lista.append(banco_simples(
        "02-linha-quebrada.pdf", "linha partida em 2 linhas, com pontos e espaços (armadilha 6)",
        "237", "Banco Bradesco S.A.", date(2026, 11, 5), 124990, "2090000000000002000000002",
        quebrar_linha=True))
    lista.append(banco_simples(
        "03-numeros-vizinhos.pdf", "CNPJ, nosso número e número colado na linha (armadilha 7)",
        "001", "Banco do Brasil S.A.", date(2026, 10, 30), 8975, "3090000000000003000000003",
        extra=["CNPJ do beneficiário (fictício): 11.222.333/0001-81",
               "Nosso número (fictício): 00012345678901234",
               "Código de referência (fictício): 9988776655443322"]))
    lista.append(banco_simples(
        "04-sem-vencimento.pdf", "fator 0000: boleto sem vencimento no código (armadilha 2)",
        "104", "CAIXA ECONOMICA FEDERAL", None, 12000, "4090000000000004000000004"))
    lista.append(banco_simples(
        "05-valor-aberto.pdf", "valor zero: valor em aberto, fora do total (armadilha 3)",
        "033", "BANCO SANTANDER (BRASIL) S.A.", date(2026, 10, 20), 0, "5090000000000005000000005"))

    luz = codigo_consumo("3", "8", 18745, "00010000000000000000000000006")
    lista.append(Exemplo(
        "06-conta-de-luz.pdf", "conta de consumo (energia), 3º dígito 8: vencimento fora do código (armadilha 4)",
        "Companhia de Energia Exemplo",
        [Boleto(L.formatar(L.codigo_para_linha(luz)), "Energia elétrica e gás", "R$ 187,45",
                L.CONSULTE_O_BOLETO, L.CONSULTE_O_BOLETO)],
        "R$ 187,45", "20/10/2026"))

    iptu = codigo_consumo("1", "9", 12345, "00020000000000000000000000007")
    lista.append(Exemplo(
        "07-valor-referencia.pdf", "conta de consumo com 3º dígito 9: número não é valor em reais (armadilha 9)",
        "Prefeitura Exemplo",
        [Boleto(L.formatar(L.codigo_para_linha(iptu)), "Prefeitura", L.VALOR_DE_REFERENCIA,
                L.CONSULTE_O_BOLETO, L.CONSULTE_O_BOLETO, [L.VALOR_DE_REFERENCIA], False)],
        "Consulte o documento", "25/10/2026"))

    cod988 = codigo_banco("988", date(2026, 10, 12), 45678, "8090000000000008000000008")
    lista.append(Exemplo(
        "08-codigo-988.pdf", "instituição sem número de banco (988): campo 5 não é fator nem valor (armadilha 10)",
        "Instituição Exemplo de Pagamento",
        [Boleto(L.formatar(L.codigo_para_linha(cod988)), "Instituição sem número de banco (988)",
                L.CONSULTE_O_BOLETO, L.CONSULTE_O_BOLETO, L.CONSULTE_O_BOLETO,
                [L.VALOR_E_VENCIMENTO_988], False)],
        "R$ 456,78", "12/10/2026"))

    lista.append(Exemplo(
        "09-copia-do-01.pdf", "cópia exata do 01: o mesmo boleto duas vezes (armadilha 8)",
        "", [], "", "", copia_de="01-banco-normal.pdf"))

    inter = codigo_banco("077", date(2026, 11, 10), 5990, "1009000000000010000000010")
    lista.append(Exemplo(
        "10-so-codigo-de-barras.pdf", "só o código de barras (44 dígitos), sem a linha digitável",
        "Banco Inter S.A.",
        [Boleto(inter, "Banco Inter S.A. (077)", "R$ 59,90", "10/11/2026", situacao(date(2026, 11, 10)),
                [L.AVISO_CODIGO_DE_BARRAS])],
        "R$ 59,90", "10/11/2026"))

    nu = L.codigo_para_linha(codigo_banco("260", date(2026, 10, 25), 21000, "1109000000000011000000011"))
    errado = trocar_digito(nu, 14)
    lista.append(Exemplo(
        "11-digito-errado.pdf", "um dígito trocado: linha inválida, com o motivo (armadilha 5)",
        "NU PAGAMENTOS S.A.",
        [Boleto(L.formatar(errado), "—", "—", "—", L.LINHA_INVALIDA,
                ["dígito do campo 2 não confere"], False, valido=False)],
        "R$ 210,00", "25/10/2026"))

    bb = L.codigo_para_linha(codigo_banco("001", date(2026, 10, 18), 7890, "1209000000000012000000012"))
    lista.append(Exemplo(
        "12-so-imagem.pdf", "boleto como imagem, sem texto: o programa pede para colar a linha",
        "Banco do Brasil S.A.",
        [Boleto(L.formatar(bb), "—", "—", "—", L.LINHA_INVALIDA,
                ["não encontrei a linha, cole manualmente"], False, valido=False)],
        "R$ 78,90", "18/10/2026", so_imagem=True))

    c6 = [codigo_banco("336", d, 20000, f"13{n}9000000000013000000013") for n, d in
          ((1, date(2026, 10, 10)), (2, date(2026, 11, 10)))]
    lista.append(Exemplo(
        "13-carne.pdf", "carnê: dois boletos diferentes no mesmo PDF (uma linha por boleto)",
        "Banco C6 S.A.",
        [Boleto(L.formatar(L.codigo_para_linha(c)), "Banco C6 S.A. (336)", "R$ 200,00",
                data_txt(d), situacao(d)) for c, d in zip(c6, (date(2026, 10, 10), date(2026, 11, 10)))],
        "R$ 200,00", "10/10/2026 e 10/11/2026"))
    return lista


def linhas_do_boleto(ex: Exemplo, b: Boleto, parcela: int | None = None) -> list[tuple[str, str]]:
    if len(L.limpar(b.impresso)) == 44:
        corpo = [("N", "Código de barras:"), ("L", b.impresso)]
    elif ex.quebrar_linha:
        partes = b.impresso.split(" ")
        corpo = [("N", "Linha digitável:"), ("L", " ".join(partes[:2])), ("L", " ".join(partes[2:]))]
    elif ex.extra:
        corpo = [("N", "Linha digitável:"), ("L", "Doc. 20260915 " + b.impresso)]
    else:
        corpo = [("N", "Linha digitável:"), ("L", b.impresso)]
    titulo = ex.beneficiario_banco + (f" - parcela {parcela} de 2" if parcela else "")
    return [
        ("T", titulo),
        *corpo,
        ("N", "Beneficiário: Exemplo Ltda (fictício)"),
        ("N", "Pagador: Fulano de Teste (fictício)"),
        *[("N", t) for t in ex.extra],
        ("N", f"Vencimento: {b.vencimento if parcela else ex.vencimento_impresso}"),
        ("N", f"Valor do documento: {ex.valor_impresso}"),
    ]


def pdf_novo() -> FPDF:
    pdf = FPDF(format="A4")
    pdf.set_creation_date(CRIACAO)
    pdf.set_author("Leitor de boletos - exemplo fictício")
    pdf.set_title(SELO)
    pdf.set_auto_page_break(False)
    return pdf


def desenhar_texto(pdf: FPDF, linhas: list[tuple[str, str]], y: float) -> float:
    pdf.set_draw_color(120, 120, 120)
    topo = y
    for estilo, texto in linhas:
        if estilo == "T":
            pdf.set_font("Helvetica", "B", 13)
        elif estilo == "L":
            pdf.set_font("Courier", "B", 11)
        else:
            pdf.set_font("Helvetica", "", 10)
        pdf.set_xy(20, y)
        pdf.cell(170, 7, texto)
        y += 8
    pdf.rect(15, topo - 3, 180, y - topo + 4)
    return y + 8


def desenhar_selo(pdf: FPDF) -> None:
    pdf.set_fill_color(255, 235, 200)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(15, 15)
    pdf.cell(180, 12, SELO, align="C", fill=True)


def imagem_do_boleto(linhas: list[tuple[str, str]]) -> io.BytesIO:
    img = Image.new("RGB", (1500, 700), "white")
    desenho = ImageDraw.Draw(img)
    fonte = ImageFont.load_default(size=30)
    y = 30
    for _, texto in [("T", SELO), *linhas]:
        desenho.text((30, y), texto, fill="black", font=fonte)
        y += 50
    saida = io.BytesIO()
    img.save(saida, format="PNG")
    saida.seek(0)
    return saida


def gerar_pdf(ex: Exemplo) -> None:
    destino = SAIDA / ex.arquivo
    if ex.copia_de:
        shutil.copyfile(SAIDA / ex.copia_de, destino)
        return
    pdf = pdf_novo()
    pdf.add_page()
    if ex.so_imagem:
        pdf.image(imagem_do_boleto(linhas_do_boleto(ex, ex.boletos[0])), x=15, y=20, w=180)
    else:
        desenhar_selo(pdf)
        y = 40
        varios = len(ex.boletos) > 1
        for i, b in enumerate(ex.boletos, start=1):
            y = desenhar_texto(pdf, linhas_do_boleto(ex, b, i if varios else None), y)
    pdf.output(str(destino))


def gabarito(lista: list[Exemplo]) -> str:
    por_nome = {e.arquivo: e for e in lista}
    partes = [
        "# Exemplos fictícios - gabarito",
        "",
        "Gerados por `scripts/gerar_exemplos.py`. **Nenhum é boleto real**: empresa, pagador,",
        "documentos e números são inventados, e cada PDF traz o selo \"" + SELO + "\".",
        "",
        "Resultado esperado da leitura de cada arquivo, com a data de hoje = 29/09/2026.",
        "",
        "| Arquivo | O que prova | Banco | Valor | Vencimento | Situação | Avisos | Entra no total |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for ex in lista:
        boletos = por_nome[ex.copia_de].boletos if ex.copia_de else ex.boletos
        for b in boletos:
            avisos = list(b.avisos) + (["duplicado"] if ex.copia_de else [])
            entra = b.entra_no_total and not ex.copia_de
            partes.append(
                f"| `{ex.arquivo}` | {ex.cobre} | {b.banco} | {b.valor} | {b.vencimento} | "
                f"{b.situacao} | {'; '.join(avisos) or '-'} | {'sim' if entra else 'não'} |"
            )
    total = sum(
        Decimal(b.valor.replace("R$ ", "").replace(".", "").replace(",", "."))
        for ex in lista if not ex.copia_de for b in ex.boletos
        if b.entra_no_total and b.valor.startswith("R$")
    )
    partes += ["", f"**Total esperado com os 13 arquivos carregados juntos: {L.formatar_reais(total)}**"]
    return "\n".join(partes) + "\n"


def main() -> None:
    SAIDA.mkdir(exist_ok=True)
    lista = exemplos()
    for ex in lista:
        gerar_pdf(ex)
    (SAIDA / "LEIA-ME.md").write_text(gabarito(lista), encoding="utf-8")
    print(f"{len(lista)} exemplos gerados em {SAIDA}")


if __name__ == "__main__":
    main()
