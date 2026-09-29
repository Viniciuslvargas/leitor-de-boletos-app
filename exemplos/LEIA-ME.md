# Exemplos fictícios - gabarito

Gerados por `scripts/gerar_exemplos.py`. **Nenhum é boleto real**: empresa, pagador,
documentos e números são inventados, e cada PDF traz o selo "EXEMPLO FICTÍCIO - NÃO É UM BOLETO REAL".

Resultado esperado da leitura de cada arquivo, com a data de hoje = 29/09/2026.

| Arquivo | O que prova | Banco | Valor | Vencimento | Situação | Avisos | Entra no total |
|---|---|---|---|---|---|---|---|
| `01-banco-normal.pdf` | caso comum; vencimento no ciclo novo do fator (armadilha 1) | ITAÚ UNIBANCO S.A. (341) | R$ 350,00 | 15/10/2026 | vence em 16 dias | - | sim |
| `02-linha-quebrada.pdf` | linha partida em 2 linhas, com pontos e espaços (armadilha 6) | Banco Bradesco S.A. (237) | R$ 1.249,90 | 05/11/2026 | vence em 37 dias | - | sim |
| `03-numeros-vizinhos.pdf` | CNPJ, nosso número e número colado na linha (armadilha 7) | Banco do Brasil S.A. (001) | R$ 89,75 | 30/10/2026 | vence em 31 dias | - | sim |
| `04-sem-vencimento.pdf` | fator 0000: boleto sem vencimento no código (armadilha 2) | CAIXA ECONOMICA FEDERAL (104) | R$ 120,00 | sem vencimento | sem vencimento | - | sim |
| `05-valor-aberto.pdf` | valor zero: valor em aberto, fora do total (armadilha 3) | BANCO SANTANDER (BRASIL) S.A. (033) | valor em aberto | 20/10/2026 | vence em 21 dias | - | não |
| `06-conta-de-luz.pdf` | conta de consumo (energia), 3º dígito 8: vencimento fora do código (armadilha 4) | Energia elétrica e gás | R$ 187,45 | consulte o boleto | consulte o boleto | - | sim |
| `07-valor-referencia.pdf` | conta de consumo com 3º dígito 9: número não é valor em reais (armadilha 9) | Prefeitura | valor de referência, consulte o boleto | consulte o boleto | consulte o boleto | valor de referência, consulte o boleto | não |
| `08-codigo-988.pdf` | instituição sem número de banco (988): campo 5 não é fator nem valor (armadilha 10) | Instituição sem número de banco (988) | consulte o boleto | consulte o boleto | consulte o boleto | valor e vencimento: consulte o boleto | não |
| `09-copia-do-01.pdf` | cópia exata do 01: o mesmo boleto duas vezes (armadilha 8) | ITAÚ UNIBANCO S.A. (341) | R$ 350,00 | 15/10/2026 | vence em 16 dias | duplicado | não |
| `10-so-codigo-de-barras.pdf` | só o código de barras (44 dígitos), sem a linha digitável | Banco Inter S.A. (077) | R$ 59,90 | 10/11/2026 | vence em 42 dias | lido pelo código de barras | sim |
| `11-digito-errado.pdf` | um dígito trocado: linha inválida, com o motivo (armadilha 5) | — | — | — | linha inválida | dígito do campo 2 não confere | não |
| `12-so-imagem.pdf` | boleto como imagem, sem texto: o programa pede para colar a linha | — | — | — | linha inválida | não encontrei a linha, cole manualmente | não |
| `13-carne.pdf` | carnê: dois boletos diferentes no mesmo PDF (uma linha por boleto) | Banco C6 S.A. (336) | R$ 200,00 | 10/10/2026 | vence em 11 dias | - | sim |
| `13-carne.pdf` | carnê: dois boletos diferentes no mesmo PDF (uma linha por boleto) | Banco C6 S.A. (336) | R$ 200,00 | 10/11/2026 | vence em 42 dias | - | sim |

**Total esperado com os 13 arquivos carregados juntos: R$ 2.457,00**
