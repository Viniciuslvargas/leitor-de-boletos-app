import os
import sys
from datetime import date
from pathlib import Path
from tkinter import filedialog, ttk

import customtkinter as ctk

from . import __version__
from . import linha as L
from .linha import Boleto
from .pdf import ler_pdf
from .planilha import aviso_texto, descrever_fora, exportar_csv, exportar_xlsx, nome_sugerido
from .tabela import montar

FONTE = "Segoe UI"
AZUL = "#1f6aa5"

CORES = {
    "Light": {
        "fundo": "#f3f3f3", "painel": "#ffffff", "cabecalho": "#f7f7f7", "texto": "#1b1b1b",
        "suave": "#5c5c5c", "borda": "#c9c9c9", "linha": "#e3e3e3", "selecao": "#cfe3f4",
        "confira": ("#fff4ce", "#4d3800"), "problema": ("#fde7e9", "#7a1620"),
        "circulo": ("#e3eef8", "#144870"), "erro": "#a4262c",
    },
    "Dark": {
        "fundo": "#1c1c1c", "painel": "#2b2b2b", "cabecalho": "#323232", "texto": "#f3f3f3",
        "suave": "#b8b8b8", "borda": "#4a4a4a", "linha": "#3a3a3a", "selecao": "#1f4e73",
        "confira": ("#3d3319", "#f7d98b"), "problema": ("#4a2327", "#f6b8be"),
        "circulo": ("#1f3a52", "#cfe3f4"), "erro": "#f28b92",
    },
}

COLUNAS = [
    ("arquivo", "Arquivo", 150, "w"),
    ("banco", "Banco", 175, "w"),
    ("valor", "Valor", 115, "e"),
    ("vencimento", "Vencimento", 105, "w"),
    ("situacao", "Situação", 125, "w"),
    ("linha", "Linha digitável", 300, "w"),
    ("aviso", "Aviso", 230, "w"),
]

PASSOS = [
    ("1", "Escolha os PDFs",
     "Um ou vários de uma vez. Boleto que veio como texto? Cole a linha no campo lá em cima."),
    ("2", "Confira a tabela",
     "Linha amarela pede conferência. Linha vermelha tem problema e diz o motivo."),
    ("3", "Exporte", "Salve a planilha para o Excel ou em CSV, com o total somado."),
]

LUA, SOL = "☾", "☼"


class App(ctk.CTk):
    def __init__(self, hoje: date | None = None):
        super().__init__()
        self.hoje = hoje or date.today()
        self.boletos: list[Boleto] = []
        self.aviso_flutuante: ctk.CTkFrame | None = None

        self.title("Leitor de boletos")
        self.geometry("1200x750")
        self.minsize(960, 600)
        icone = Path(__file__).resolve().parent / "dados" / "icone.ico"
        if icone.exists():
            self.iconbitmap(str(icone))

        self._montar_barra()
        self.conteudo = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.conteudo.pack(fill="both", expand=True)
        self._montar_guia()
        self._montar_tabela()
        self._montar_rodape()

        self._aplicar_cores()
        self._atualizar()


    def _montar_barra(self) -> None:
        self.barra = ctk.CTkFrame(self, corner_radius=0, height=80)
        self.barra.pack(fill="x")
        self.barra.grid_columnconfigure(3, weight=1)

        self.bt_pdfs = ctk.CTkButton(
            self.barra, text="Escolher PDFs", height=44, width=150, corner_radius=8,
            fg_color=AZUL, font=(FONTE, 14, "bold"), command=self.escolher_pdfs)
        self.bt_pdfs.grid(row=0, column=0, padx=(20, 8), pady=18)

        self.sep1 = ctk.CTkFrame(self.barra, width=1, height=40)
        self.sep1.grid(row=0, column=1, padx=6)
        self.rotulo_colar = ctk.CTkLabel(self.barra, text="Ou cole a linha", font=(FONTE, 13))
        self.rotulo_colar.grid(row=0, column=2, padx=(6, 8))

        self.campo = ctk.CTkEntry(
            self.barra, height=40, corner_radius=8, font=("Consolas", 13),
            placeholder_text="10490.05505 77222.133348 77777.777713 4 32420000032112")
        self.campo.grid(row=0, column=3, sticky="ew")
        self.campo.bind("<Return>", lambda _e: self.colar_linha())
        self.campo.bind("<Key>", lambda _e: self._limpar_erro_campo())
        self.erro_campo = ctk.CTkLabel(self.barra, text="", font=(FONTE, 12), anchor="w")
        self.erro_campo.grid(row=1, column=3, columnspan=8, sticky="w", pady=(0, 8))
        self.erro_campo.grid_remove()

        self.bt_adicionar = self._botao_contorno("Adicionar", self.colar_linha)
        self.bt_adicionar.grid(row=0, column=4, padx=(8, 6))
        self.sep2 = ctk.CTkFrame(self.barra, width=1, height=40)
        self.sep2.grid(row=0, column=5, padx=6)
        self.bt_excel = self._botao_contorno("Exportar Excel", lambda: self.exportar("xlsx"))
        self.bt_excel.grid(row=0, column=6, padx=4)
        self.bt_csv = self._botao_contorno("Exportar CSV", lambda: self.exportar("csv"))
        self.bt_csv.grid(row=0, column=7, padx=4)
        self.bt_limpar = self._botao_leve("Limpar", self.limpar)
        self.bt_limpar.grid(row=0, column=8, padx=2)
        self.bt_ajuda = self._botao_leve("Como usar", self.como_usar)
        self.bt_ajuda.grid(row=0, column=9, padx=2)
        self.bt_tema = ctk.CTkButton(
            self.barra, text=LUA, width=40, height=40, corner_radius=8, border_width=1,
            font=(FONTE, 18), command=self.alternar_tema)
        self.bt_tema.grid(row=0, column=10, padx=(4, 20))

    def _botao_contorno(self, texto: str, comando) -> ctk.CTkButton:
        return ctk.CTkButton(self.barra, text=texto, height=40, corner_radius=8, border_width=1,
                             font=(FONTE, 14), command=comando, width=0)

    def _botao_leve(self, texto: str, comando) -> ctk.CTkButton:
        return ctk.CTkButton(self.barra, text=texto, height=40, corner_radius=8,
                             font=(FONTE, 14), command=comando, width=0)

    def _montar_guia(self) -> None:
        self.guia = ctk.CTkFrame(self.conteudo, fg_color="transparent")
        centro = ctk.CTkFrame(self.guia, fg_color="transparent")
        centro.place(relx=0.5, rely=0.5, anchor="center")
        self.guia_titulo = ctk.CTkLabel(centro, text="Leia seus boletos em segundos",
                                        font=(FONTE, 26, "bold"))
        self.guia_titulo.pack()
        self.guia_sub = ctk.CTkLabel(centro, font=(FONTE, 15),
                                     text="Tudo roda no seu computador. Nenhum boleto sai daqui.")
        self.guia_sub.pack(pady=(4, 32))
        cartoes = ctk.CTkFrame(centro, fg_color="transparent")
        cartoes.pack()
        self.cartoes = []
        for numero, titulo, texto in PASSOS:
            cartao = ctk.CTkFrame(cartoes, width=260, height=200, corner_radius=12, border_width=1)
            cartao.pack(side="left", padx=12)
            cartao.pack_propagate(False)
            circulo = ctk.CTkLabel(cartao, text=numero, width=48, height=48, corner_radius=24,
                                   font=(FONTE, 20, "bold"))
            circulo.pack(pady=(28, 12))
            ctk.CTkLabel(cartao, text=titulo, font=(FONTE, 17, "bold")).pack()
            descricao = ctk.CTkLabel(cartao, text=texto, font=(FONTE, 14), wraplength=210,
                                     justify="center")
            descricao.pack(pady=(8, 0), padx=20)
            self.cartoes.append((cartao, circulo, descricao))

    def _montar_tabela(self) -> None:
        self.moldura = ctk.CTkFrame(self.conteudo, corner_radius=8, border_width=1)
        self.estilo = ttk.Style(self)
        self.estilo.theme_use("clam")
        self.arvore = ttk.Treeview(self.moldura, columns=[c[0] for c in COLUNAS],
                                   show="headings", style="Boletos.Treeview")
        for chave, titulo, largura, lado in COLUNAS:
            self.arvore.heading(chave, text=titulo, anchor=lado)
            self.arvore.column(chave, width=largura, minwidth=60, anchor=lado, stretch=False)
        rolagem_v = ctk.CTkScrollbar(self.moldura, command=self.arvore.yview)
        self.arvore.configure(yscrollcommand=rolagem_v.set)
        self.arvore.grid(row=0, column=0, sticky="nsew", padx=(2, 0), pady=2)
        rolagem_v.grid(row=0, column=1, sticky="ns", pady=2)
        self.moldura.grid_rowconfigure(0, weight=1)
        self.moldura.grid_columnconfigure(0, weight=1)
        self.arvore.bind("<Configure>", self._ajustar_colunas)

    def _ajustar_colunas(self, evento) -> None:
        base = sum(c[2] for c in COLUNAS)
        disponivel = max(evento.width - 4, base // 2)
        for chave, _, largura, _ in COLUNAS:
            self.arvore.column(chave, width=int(disponivel * largura / base))

    def _montar_rodape(self) -> None:
        self.rodape = ctk.CTkFrame(self, corner_radius=0, height=44)
        self.rodape.pack(fill="x", side="bottom")
        self.resumo = ctk.CTkLabel(self.rodape, text="", font=(FONTE, 13), anchor="w")
        self.resumo.pack(side="left", padx=20, pady=10)
        self.total = ctk.CTkLabel(self.rodape, text="", font=(FONTE, 17, "bold"))
        self.total.pack(side="right", padx=20)


    def _cores(self) -> dict:
        return CORES[ctk.get_appearance_mode()]

    def _aplicar_cores(self) -> None:
        c = self._cores()
        self.configure(fg_color=c["fundo"])
        for painel in (self.barra, self.rodape):
            painel.configure(fg_color=c["painel"])
        for separador in (self.sep1, self.sep2):
            separador.configure(fg_color=c["linha"])
        self.rotulo_colar.configure(text_color=c["suave"])
        self.campo.configure(fg_color=c["fundo"], border_color=c["borda"], text_color=c["texto"])
        self.erro_campo.configure(text_color=c["erro"])
        for botao in (self.bt_adicionar, self.bt_excel, self.bt_csv, self.bt_tema):
            botao.configure(fg_color=c["painel"], hover_color=c["linha"],
                            border_color=c["borda"], text_color=c["texto"])
        for botao in (self.bt_limpar, self.bt_ajuda):
            botao.configure(fg_color="transparent", hover_color=c["linha"], text_color=c["texto"])
        self.bt_tema.configure(text=SOL if ctk.get_appearance_mode() == "Dark" else LUA)
        self.guia_sub.configure(text_color=c["suave"])
        for cartao, circulo, descricao in self.cartoes:
            cartao.configure(fg_color=c["painel"], border_color=c["linha"])
            circulo.configure(fg_color=c["circulo"][0], text_color=c["circulo"][1])
            descricao.configure(text_color=c["suave"])
        self.moldura.configure(fg_color=c["painel"], border_color=c["linha"])
        self.resumo.configure(text_color=c["suave"])

        self.estilo.configure("Boletos.Treeview", background=c["painel"],
                              fieldbackground=c["painel"], foreground=c["texto"],
                              rowheight=32, font=(FONTE, 10), borderwidth=0)
        self.estilo.configure("Boletos.Treeview.Heading", background=c["cabecalho"],
                              foreground=c["suave"], font=(FONTE, 10, "bold"),
                              relief="flat", padding=(8, 6))
        self.estilo.map("Boletos.Treeview", background=[("selected", c["selecao"])],
                        foreground=[("selected", c["texto"])])
        self.estilo.map("Boletos.Treeview.Heading", background=[("active", c["linha"])])
        self.estilo.configure("Boletos.Treeview", bordercolor=c["painel"],
                              lightcolor=c["painel"], darkcolor=c["painel"])
        self.arvore.tag_configure("confira", background=c["confira"][0], foreground=c["confira"][1])
        self.arvore.tag_configure("problema", background=c["problema"][0],
                                  foreground=c["problema"][1])

    def alternar_tema(self) -> None:
        ctk.set_appearance_mode("Light" if ctk.get_appearance_mode() == "Dark" else "Dark")
        self._aplicar_cores()


    def escolher_pdfs(self) -> None:
        caminhos = filedialog.askopenfilenames(
            parent=self, title="Escolher boletos em PDF", filetypes=[("Boletos em PDF", "*.pdf")])
        if not caminhos:
            return
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            self.carregar(caminhos)
        finally:
            self.configure(cursor="")

    def carregar(self, caminhos) -> None:
        caminhos = list(caminhos)
        for numero, caminho in enumerate(caminhos, start=1):
            if len(caminhos) > 5:
                self.resumo.configure(text=f"Lendo {numero} de {len(caminhos)}: {Path(caminho).name}")
                self.update_idletasks()
            self.boletos.extend(ler_pdf(Path(caminho), self.hoje))
        self._atualizar()

    def colar_linha(self) -> None:
        texto = self.campo.get().strip()
        digitos = L.limpar(texto)
        if not digitos:
            self._mostrar_erro_campo("Cole a linha digitável antes de adicionar.")
            return
        if len(digitos) not in (44, 47, 48):
            self._mostrar_erro_campo(
                f"A linha precisa ter 44, 47 ou 48 números. Esta tem {len(digitos)}. "
                "Confira se copiou a linha inteira.")
            return
        self.boletos.append(L.interpretar(texto, self.hoje, "colada"))
        self.campo.delete(0, "end")
        self._limpar_erro_campo()
        self._atualizar()

    def _mostrar_erro_campo(self, mensagem: str) -> None:
        self.erro_campo.configure(text=mensagem)
        self.erro_campo.grid()
        self.campo.configure(border_color=self._cores()["erro"], border_width=2)

    def _limpar_erro_campo(self) -> None:
        if self.erro_campo.winfo_ismapped():
            self.erro_campo.grid_remove()
            self.campo.configure(border_color=self._cores()["borda"], border_width=1)

    def limpar(self) -> None:
        self.boletos = []
        if self.aviso_flutuante is not None and self.aviso_flutuante.winfo_exists():
            self.aviso_flutuante.destroy()
        self._limpar_erro_campo()
        self._atualizar()

    def exportar(self, extensao: str) -> None:
        if not self.boletos:
            self._avisar("Nada para exportar", "Carregue boletos antes de exportar.", erro=True)
            return
        tipos = {"xlsx": [("Planilha do Excel", "*.xlsx")], "csv": [("Arquivo CSV", "*.csv")]}
        destino = filedialog.asksaveasfilename(
            parent=self, title="Salvar planilha", defaultextension=f".{extensao}",
            initialfile=nome_sugerido(self.hoje, extensao), filetypes=tipos[extensao])
        if not destino:
            return
        try:
            tabela = montar(self.boletos)
            (exportar_xlsx if extensao == "xlsx" else exportar_csv)(tabela, destino)
        except PermissionError:
            self._avisar("Não consegui salvar",
                         "O arquivo está aberto no Excel. Feche o arquivo e tente de novo.", erro=True)
        except OSError:
            self._avisar("Não consegui salvar",
                         "Escolha outra pasta e tente de novo.", erro=True)
        else:
            self._avisar("Planilha salva", str(Path(destino)), pasta=Path(destino).parent)

    def _avisar(self, titulo: str, texto: str, erro: bool = False, pasta: Path | None = None) -> None:
        if self.aviso_flutuante is not None:
            self.aviso_flutuante.destroy()
        c = self._cores()
        caixa = ctk.CTkFrame(self, corner_radius=10, border_width=1, fg_color=c["painel"],
                             border_color=c["erro"] if erro else "#9fd3a8")
        ctk.CTkLabel(caixa, text=titulo, font=(FONTE, 14, "bold"), text_color=c["texto"],
                     anchor="w").pack(fill="x", padx=18, pady=(14, 0))
        ctk.CTkLabel(caixa, text=texto, font=(FONTE, 13), text_color=c["suave"], anchor="w",
                     wraplength=380, justify="left").pack(fill="x", padx=18, pady=(2, 8))
        botoes = ctk.CTkFrame(caixa, fg_color="transparent")
        botoes.pack(fill="x", padx=14, pady=(0, 12))
        if pasta is not None:
            ctk.CTkButton(botoes, text="Abrir pasta", width=0, height=32, border_width=1,
                          fg_color=c["painel"], border_color=c["borda"], text_color=c["texto"],
                          hover_color=c["linha"], command=lambda: os.startfile(pasta)).pack(side="left", padx=4)
        ctk.CTkButton(botoes, text="Fechar", width=0, height=32, fg_color="transparent",
                      text_color=c["texto"], hover_color=c["linha"],
                      command=caixa.destroy).pack(side="left", padx=4)
        caixa.place(relx=1.0, rely=1.0, x=-36, y=-64, anchor="se")
        self.aviso_flutuante = caixa
        self.after(8000, lambda: caixa.winfo_exists() and caixa.destroy())

    def como_usar(self) -> None:
        c = self._cores()
        janela = ctk.CTkToplevel(self)
        janela.title("Como usar")
        janela.geometry("700x560")
        janela.resizable(False, False)
        janela.transient(self)
        janela.configure(fg_color=c["painel"])
        corpo = ctk.CTkFrame(janela, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=32, pady=24)

        def texto(t, tamanho=14, negrito=False, cor=None, **kw):
            rotulo = ctk.CTkLabel(corpo, text=t, font=(FONTE, tamanho, "bold" if negrito else "normal"),
                                  text_color=cor or c["texto"], anchor="w", justify="left",
                                  wraplength=630, **kw)
            rotulo.pack(fill="x", pady=4)
            return rotulo

        texto("Como usar", 22, True)
        texto("1. Clique em Escolher PDFs e selecione um ou vários boletos. Boleto que chegou "
              "como texto: cole a linha digitável no campo e tecle Enter.")
        texto("2. Confira a tabela. O total embaixo soma só os boletos com valor certo em reais.")
        texto("3. Clique em Exportar Excel ou Exportar CSV e escolha onde salvar.")
        texto("O que as cores querem dizer", 15, True).pack_configure(pady=(14, 4))
        for chave, titulo, explicacao in (
            ("confira", "Amarelo: confira",
             "Duplicado, valor em aberto, valor de referência, data incomum, código 988 ou lido "
             "pelo código de barras. Esses boletos ficam fora do total ou pedem uma olhada no boleto."),
            ("problema", "Vermelho: problema",
             "Os números não conferem, ou o PDF não tem texto. A coluna Aviso diz o motivo. "
             "Cole a linha manualmente."),
        ):
            fundo, frente = c[chave]
            faixa = ctk.CTkFrame(corpo, fg_color=fundo, corner_radius=8)
            faixa.pack(fill="x", pady=4)
            ctk.CTkLabel(faixa, text=f"{titulo}  ·  {explicacao}", font=(FONTE, 13),
                         text_color=frente, anchor="w", justify="left",
                         wraplength=600).pack(fill="x", padx=12, pady=10)
        texto("O programa não lê foto nem PDF escaneado, não paga boleto e não guarda nada: "
              "fechou, apagou.", 13, cor=c["suave"]).pack_configure(pady=(12, 4))
        rodape = ctk.CTkFrame(corpo, fg_color="transparent")
        rodape.pack(fill="x", pady=(12, 0))
        ctk.CTkLabel(rodape, text=f"Leitor de boletos {__version__} · código aberto (licença MIT)",
                     font=(FONTE, 12), text_color=c["suave"]).pack(side="left")
        ctk.CTkButton(rodape, text="Entendi", width=120, height=40, fg_color=AZUL,
                      font=(FONTE, 14, "bold"), command=janela.destroy).pack(side="right")
        janela.after(50, janela.grab_set)


    def _atualizar(self) -> None:
        tabela = montar(self.boletos)
        if not tabela.linhas:
            self.moldura.pack_forget()
            self.guia.pack(fill="both", expand=True)
            self.resumo.configure(text="Nenhum boleto carregado")
            self.total.configure(text="Total: R$ 0,00")
            return

        self.guia.pack_forget()
        self.moldura.pack(fill="both", expand=True, padx=20, pady=16)
        self.arvore.delete(*self.arvore.get_children())
        for boleto in tabela.linhas:
            if not boleto.valido:
                tag = ("problema",)
            elif boleto.avisos or not boleto.entra_no_total:
                tag = ("confira",)
            else:
                tag = ()
            self.arvore.insert("", "end", tags=tag, values=(
                boleto.origem, boleto.banco or "—", boleto.valor_texto, boleto.vencimento_texto,
                boleto.situacao, L.formatar(boleto.numero) if boleto.numero else "—",
                aviso_texto(boleto)))

        no_total = sum(1 for b in tabela.linhas if b.entra_no_total)
        resumo = f"{len(tabela.linhas)} boletos · {no_total} no total"
        fora = len(tabela.linhas) - no_total
        if fora:
            resumo += f" · {fora} fora do total ({descrever_fora(tabela)})"
        self.resumo.configure(text=resumo)
        self.total.configure(text=f"Total: {L.formatar_reais(tabela.total)}")


def autoteste(pasta: str, saida: str) -> None:
    app = App()

    def rodar():
        app.carregar(sorted(Path(pasta).glob("*.pdf")))
        tabela = montar(app.boletos)
        Path(saida).write_text(
            f"linhas={len(tabela.linhas)} total={tabela.total} fora={descrever_fora(tabela)}\n",
            encoding="utf-8")
        app.after(800, app.destroy)

    app.after(500, rodar)
    app.mainloop()


def main() -> None:
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    if len(sys.argv) == 4 and sys.argv[1] == "--autoteste":
        autoteste(sys.argv[2], sys.argv[3])
        return
    App().mainloop()


if __name__ == "__main__":
    main()
