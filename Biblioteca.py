import csv
import io
import math
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

arquivoLivros = os.path.join(BASE_DIR, "Arquivos", "Livros.csv")
arquivoCategorias = os.path.join(BASE_DIR, "Arquivos", "Categorias.csv")
arquivoListaDesejo = os.path.join(BASE_DIR, "Arquivos", "ListaDesejos.csv")

# Cores ANSI
vermelho = "\033[91m"
verde = "\033[32m"
amarelo = "\033[33m"
azul = "\033[34m"
azulClaro = "\033[94m"
fimCor = "\033[m"

# Alinhamentos de tabela
LARGURA_TITULO = 30
LARGURA_CATEGORIA = 22
LARGURA_AUTOR = 20

linha0 = "| {:<30} | {:^22} | {:^20} | {:^11}"  # cabecalho sem favorito
linha1 = "| {:<30} | {:^9} | {:^22} | {:^20} | {:^11}"  # cabecalho com favorito
linha2 = "| {:<30} | {} | {:^22} | {:^20} | R${:>9,.2f}"  # linha com favorito e valor
linha3 = "| {:<30} | {:^22} | {:^20} | R${:>9,.2f}"  # linha sem favorito e com valor

# Formatação dos Menus
separador = f"{azul}=-={fimCor}" * 8
menuStarte = "{:<2}{}".format("", f"{vermelho}(ENTER){fimCor} Para iniciar")
menuMain = "{:<5}{}".format("", "MENU PRINCIPAL")
menuMeusLivros = "{:<6}{}".format("", "MEUS LIVROS")
menuNovoLivro = "{:<6}{}".format("", "NOVO LIVRO")
menuListaCat = "{:<6}{}".format("", "LISTA CATEGORIA")
menuListaAutor = "{:<6}{}".format("", "LISTA AUTOR")
menuListaFav = "{:<6}{}".format("", "LISTA FAVORITOS")
menuListaDj = "{:<4}{}".format("", "LISTA DE DESEJOS")

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _limpar_tela():
    """Limpa o terminal de forma compatível com Windows e Unix."""
    os.system("cls" if os.name == "nt" else "clear")


def _garantir_arquivo(caminho):
    """Garante que o diretório pai e o arquivo existam."""
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    if not os.path.exists(caminho):
        with open(caminho, "a", encoding="utf-8", newline=""):
            pass


def _largura_visivel(texto):
    """Retorna o tamanho de exibição do texto ignorando sequências ANSI."""
    return len(_ANSI_RE.sub("", texto))


def _truncar(texto, limite):
    """Trunca texto excedente para preservar o alinhamento das colunas."""
    if len(texto) <= limite:
        return texto
    return texto[: limite - 3] + "..."


def _ler_categorias():
    """Lê as categorias cadastradas ignorando linhas em branco."""
    _garantir_arquivo(arquivoCategorias)
    with open(arquivoCategorias, "r", encoding="utf-8", newline="") as arquivo:
        return [linha.strip() for linha in arquivo if linha.strip()]


def _buscar_categoria(nome, categorias):
    """Busca categoria pelo nome sem diferenciar maiúsculas e minúsculas."""
    alvo = nome.strip().casefold()
    for categoria in categorias:
        if categoria.strip().casefold() == alvo:
            return categoria.strip()
    return None


def _adicionar_categoria(categoria_op):
    """Adiciona uma nova categoria caso ela ainda não exista (case-insensitive)."""
    nome = categoria_op.strip()
    if not nome:
        return ""
    categorias = _ler_categorias()
    existente = _buscar_categoria(nome, categorias)
    if existente:
        return existente
    categorias.append(nome)
    with open(arquivoCategorias, "w", encoding="utf-8", newline="") as arquivo:
        arquivo.writelines(f"{cat}\n" for cat in categorias)
    return nome


def _contar_livros_por_categoria(nome):
    """Retorna quantos registros em Meus Livros e Lista de Desejos usam a categoria."""
    alvo = nome.strip().casefold()
    total = 0
    for caminho, com_fav, idx_cat in ((arquivoLivros, True, 2), (arquivoListaDesejo, False, 1)):
        _, validos, _ = _carregar_linhas_arquivo(caminho, com_favorito=com_fav)
        total += sum(1 for _, campos, _ in validos if campos[idx_cat].casefold() == alvo)
    return total


def _editar_categoria(antiga, nova):
    """Renomeia uma categoria e atualiza livros/desejos vinculados sem perder linhas malformadas."""
    nome_novo = nova.strip()
    if not nome_novo:
        return False, "O nome da categoria não pode ficar vazio."

    categorias = _ler_categorias()
    alvo = antiga.strip().casefold()
    indice = next((i for i, c in enumerate(categorias) if c.casefold() == alvo), None)
    if indice is None:
        return False, "Categoria original não encontrada."

    conflito = _buscar_categoria(nome_novo, categorias)
    if conflito and conflito.casefold() != alvo:
        return False, f'Já existe uma categoria chamada "{conflito}".'

    categorias[indice] = nome_novo
    with open(arquivoCategorias, "w", encoding="utf-8", newline="") as arquivo:
        arquivo.writelines(f"{cat}\n" for cat in categorias)

    for caminho, com_fav, idx_cat in ((arquivoLivros, True, 2), (arquivoListaDesejo, False, 1)):
        linhas_brutas, validos, _ = _carregar_linhas_arquivo(caminho, com_favorito=com_fav)
        alterou = False
        for idx_bruto, campos, valor in validos:
            if campos[idx_cat].casefold() == alvo:
                campos[idx_cat] = nome_novo
                linhas_brutas[idx_bruto] = _formatar_linha_csv(campos, valor)
                alterou = True
        if alterou:
            _salvar_linhas_brutas(caminho, linhas_brutas)

    return True, nome_novo


def _deletar_categoria(nome):
    """Remove uma categoria de Categorias.csv (case-insensitive)."""
    alvo = nome.strip().casefold()
    categorias = _ler_categorias()
    restantes = [cat for cat in categorias if cat.casefold() != alvo]
    if len(restantes) == len(categorias):
        return False
    with open(arquivoCategorias, "w", encoding="utf-8", newline="") as arquivo:
        arquivo.writelines(f"{cat}\n" for cat in restantes)
    return True


def _formatar_linha_csv(campos, valor):
    """Serializa uma linha CSV única com escape apropriado."""
    buffer = io.StringIO()
    escritor = csv.writer(buffer, lineterminator="\n")
    escritor.writerow([*campos, f"{valor:.2f}"])
    return buffer.getvalue()


def _carregar_linhas_arquivo(caminho, com_favorito=True):
    """Lê linhas não vazias preservando linhas brutas e separando registros válidos e inválidos."""
    _garantir_arquivo(caminho)
    min_colunas = 5 if com_favorito else 4
    with open(caminho, "r", encoding="utf-8", newline="") as arquivo:
        linhas_brutas = [linha.rstrip("\r\n") + "\n" for linha in arquivo if linha.strip()]

    validos = []
    qtd_invalidas = 0
    for idx_bruto, linha_bruta in enumerate(linhas_brutas):
        linha = next(csv.reader([linha_bruta]), [])
        if len(linha) < min_colunas:
            qtd_invalidas += 1
            continue
        try:
            valor = float(linha[min_colunas - 1].strip().replace(",", "."))
        except ValueError:
            qtd_invalidas += 1
            continue
        if not math.isfinite(valor) or valor < 0:
            qtd_invalidas += 1
            continue
        campos = [campo.strip() for campo in linha[: min_colunas - 1]]
        validos.append((idx_bruto, campos, round(valor, 2)))

    return linhas_brutas, validos, qtd_invalidas


def _carregar_registros(caminho, com_favorito=True):
    """Carrega apenas os registros válidos de um arquivo CSV."""
    _, validos, _ = _carregar_linhas_arquivo(caminho, com_favorito=com_favorito)
    return [(campos, valor) for _, campos, valor in validos]


def _salvar_linhas_brutas(caminho, linhas_brutas):
    """Grava as linhas brutas no CSV preservando eventuais linhas malformadas não editadas."""
    _garantir_arquivo(caminho)
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        arquivo.writelines(linhas_brutas)


def _adicionar_registro(caminho, campos, valor):
    """Anexa um novo registro validado ao final do arquivo CSV."""
    _garantir_arquivo(caminho)
    with open(caminho, "a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, lineterminator="\n")
        escritor.writerow([*campos, f"{valor:.2f}"])


def _avisar_linhas_invalidas(qtd_invalidas):
    """Exibe aviso quando o arquivo contém linhas malformadas preservadas."""
    if qtd_invalidas > 0:
        print(
            f"{amarelo}Aviso: {qtd_invalidas} linha(s) malformada(s) "
            f"ignorada(s) na exibição e preservada(s) no arquivo.{fimCor}"
        )


def _ler_texto_obrigatorio(prompt, atual=None):
    """Solicita texto não vazio; na edição (atual != None), Enter mantém o valor atual."""
    while True:
        valor = input(prompt).strip()
        if valor:
            return valor
        if atual is not None:
            return atual
        print(f"{vermelho}Campo obrigatório! Digite um valor válido.{fimCor}")


def _ler_favorito(atual=None):
    """Lê a opção de favorito; na edição, Enter mantém o valor atual."""
    print(f"É um livro {amarelo}Favorito{fimCor} ?")
    print("1- Sim\n2- Não")
    if atual is not None:
        print(f"(Enter para manter atual: {atual})")
    print("=-=" * 8)

    favoritar = input("Opção: ").strip()
    if favoritar == "" and atual is not None:
        return atual
    if favoritar == "1":
        return "★"
    if favoritar == "2":
        return "~"

    print(f"Esta é uma opção inválida.\n{vermelho}(ENTER){fimCor} para voltar.")
    input()
    _limpar_tela()
    return None


def _ler_preco(prompt="Valor do livro: ", atual=None):
    """Lê um preço válido (aceita vírgula ou ponto, >= 0 e finito) com 2 casas decimais."""
    bruto = input(prompt).strip().replace(",", ".")
    if bruto == "" and atual is not None:
        _limpar_tela()
        return round(atual, 2)

    try:
        valor = float(bruto)
    except ValueError:
        valor = math.nan

    if not math.isfinite(valor) or valor < 0:
        _limpar_tela()
        print(f"Informação inválida!\nPressione {vermelho}(Enter){fimCor}")
        input("")
        _limpar_tela()
        return None

    _limpar_tela()
    return round(valor, 2)


def _escolher_categoria(atual=None):
    """Lista as categorias disponíveis e permite selecionar, manter ou criar uma nova."""
    categorias = _ler_categorias()
    print(separador)
    for categoria in categorias:
        print(f"- {categoria.upper()}")
    print(separador)
    print(f"\n## {amarelo}Você pode adicionar uma nova categoria{fimCor} ##\n")

    prompt = (
        f"Categoria do livro [{atual}] (Enter para manter): "
        if atual is not None
        else "Categoria do livro: "
    )
    categoria_op = _ler_texto_obrigatorio(prompt, atual=atual)
    categoria_final = _adicionar_categoria(categoria_op)
    _limpar_tela()
    return categoria_final


def _formatar_linha_tabela(campos, valor, com_favorito=True):
    """Formata uma linha da tabela de livros com truncamento e alinhamento exatos."""
    if com_favorito:
        nome, favorito, categoria, autor = campos
        simbolo = f"{favorito:^9}"
        if favorito == "★":
            simbolo = f"{amarelo}{simbolo}{fimCor}"
        return linha2.format(
            _truncar(nome, LARGURA_TITULO),
            simbolo,
            _truncar(categoria, LARGURA_CATEGORIA),
            _truncar(autor, LARGURA_AUTOR),
            valor,
        )

    nome, categoria, autor = campos
    return linha3.format(
        _truncar(nome, LARGURA_TITULO),
        _truncar(categoria, LARGURA_CATEGORIA),
        _truncar(autor, LARGURA_AUTOR),
        valor,
    )


def _imprimir_tabela(registros, com_favorito=True, numerado=False, msg_vazia=None):
    """Imprime a tabela formatada de registros e retorna a soma total dos valores."""
    if com_favorito:
        cabecalho = linha1.format("Título do Livro", "Favoritos", "Categoria", "Autor", "Valor")
    else:
        cabecalho = linha0.format("Título do Livro", "Categoria", "Autor", "Valor")

    largura_prefixo = max(3, len(str(len(registros))) + 1) if numerado else 0
    prefixo_cabecalho = " " * largura_prefixo
    largura_borda = _largura_visivel(cabecalho) + largura_prefixo

    print(f"{prefixo_cabecalho}{cabecalho}")
    print(f"{azul}={fimCor}" * largura_borda)

    soma_total = 0.0
    for idx, (campos, valor) in enumerate(registros, start=1):
        linha_txt = _formatar_linha_tabela(campos, valor, com_favorito=com_favorito)
        if numerado:
            print(f"{idx:>{largura_prefixo - 1}} {linha_txt}")
        else:
            print(linha_txt)
        soma_total += valor

    print(f"{azul}={fimCor}" * largura_borda)
    if not registros and msg_vazia:
        print(f"{amarelo}{msg_vazia}{fimCor}")
    print(f"Valor total: R$ {amarelo}{soma_total:,.2f}{fimCor} | {vermelho}(Enter){fimCor} Para voltar.")
    return soma_total


def comoUsar():
    """Exibe instruções e atalhos de uso no modo terminal e na interface gráfica."""
    print(f"{separador}\n{'':<7}COMO USAR\n{separador}")
    print("1- Adicionar livro:")
    print("   - Em Meus Livros -> 1- Novo Livro (informe Título, Favorito, Categoria, Autor e Valor).")
    print("   - Em Lista de Desejos -> 1- Novo Livro (sem campo de Favorito).")
    print("   - Dica: você pode criar novas categorias na hora e usar vírgula ou ponto no valor.")
    print("\n2- Favoritar e Desfavoritar:")
    print("   - No cadastro ou em Lista Completa -> 1- Alterar (escolha 1- Sim para ★ ou 2- Não para ~).")
    print("   - Na interface gráfica (python Interface.py): selecione o livro e aperte F ou o botão Favoritar.")
    print("\n3- Editar, Deletar e Mover:")
    print("   - Em Lista Completa ou Desejados, digite o número da linha para Alterar, Deletar (com S/N)")
    print("     ou, na Lista de Desejos da interface gráfica, Mover para Meus Livros.")
    print("   - Na edição no terminal, aperte Enter em qualquer campo para manter o valor atual.")
    print("\n4- Atalhos na Interface Gráfica (python Interface.py ou python Biblioteca.py --gui):")
    print("   - Ctrl+N: Novo Livro | Ctrl+E / Duplo clique: Editar | F: Favoritar/Desfavoritar")
    print("   - Delete: Deletar | Ctrl+F: Buscar | Ctrl+M: Mover desejo | Clique no título da coluna: Ordenar")
    print("=-=" * 8)
    input(f"Pressione {vermelho}(Enter){fimCor} para voltar.")
    _limpar_tela()


def principalMenu():
    """Exibe e gerencia o menu principal da aplicação."""
    while True:
        print(f"{separador}\n{menuMain}\n{separador}")
        print("1- Meus Livros\n2- Lista de Desejos\n3- Como Usar\n0- Encerrar")
        print("=-=" * 8)
        op_menu = input("Opção: ").strip()
        _limpar_tela()

        if op_menu == "1":
            meusLivros()
        elif op_menu == "2":
            listaDesejos()
        elif op_menu == "3":
            comoUsar()
        elif op_menu == "0":
            print(f"{vermelho}PROGRAMA FINALIZADO!{fimCor}\n")
            return
        else:
            print(f"{vermelho}Opção inválida!{fimCor}\nPressione {vermelho}(Enter){fimCor}.")
            input()
            _limpar_tela()


def meusLivros():
    """Exibe e gerencia o submenu Meus Livros."""
    while True:
        print(f"{separador}\n{menuMeusLivros}\n{separador}")
        print("1- Novo Livro\n2- Lista Completa\n3- Lista por Categoria\n4- Lista por Autor\n5- Lista por Favoritos\n0- Voltar")
        print("=-=" * 8)
        op = input("Opção: ").strip()
        _limpar_tela()

        if op == "1":
            novoLivro()
        elif op == "2":
            alterar()
        elif op == "3":
            listaCategoria()
        elif op == "4":
            listaAutor()
        elif op == "5":
            listaFavoritos()
        elif op == "0":
            return
        else:
            print(f"{vermelho}Opção inválida!{fimCor}\nPressione {vermelho}(Enter){fimCor}.")
            input()
            _limpar_tela()


def _cadastrar_item(caminho, com_favorito=True):
    """Fluxo compartilhado de cadastro para Meus Livros e Lista de Desejos."""
    print(f"{separador}\n{menuNovoLivro}\n{separador}")

    nome = _ler_texto_obrigatorio("Nome do Livro: ")
    _limpar_tela()

    favorito = None
    if com_favorito:
        favorito = _ler_favorito()
        if favorito is None:
            return
        _limpar_tela()

    categoria = _escolher_categoria()
    autor = _ler_texto_obrigatorio("Nome do autor: ")
    _limpar_tela()

    valor = _ler_preco()
    if valor is None:
        return

    campos = [nome, favorito, categoria, autor] if com_favorito else [nome, categoria, autor]
    _adicionar_registro(caminho, campos, valor)

    print(f"{separador}\n{menuNovoLivro}\n{separador}")
    print(f"\nLivro adicionado com sucesso!\nPressione {vermelho}(Enter){fimCor}")
    input("")
    _limpar_tela()


def novoLivro():
    """Cadastra um novo livro adquirido em Livros.csv."""
    _cadastrar_item(arquivoLivros, com_favorito=True)


def listaCategoria():
    """Lista livros de Livros.csv filtrados por categoria."""
    while True:
        _, validos, qtd_invalidas = _carregar_linhas_arquivo(arquivoLivros, com_favorito=True)
        categorias = _ler_categorias()

        print(f"{separador}\n{menuListaCat}\n{separador}")
        for categoria in categorias:
            print(f"- {categoria.upper()}")
        print(separador)
        print(f"{vermelho}Voltar{fimCor} => 0")

        entrada = input("Categoria desejada: ").strip()
        _limpar_tela()

        if entrada == "0":
            return

        categoria_escolhida = _buscar_categoria(entrada, categorias)
        if not categoria_escolhida:
            print(f"Essa categoria não existe.\nPressione {vermelho}(Enter){fimCor}")
            input("")
            _limpar_tela()
            continue

        filtrados = [
            (campos, valor)
            for _, campos, valor in validos
            if campos[2].casefold() == categoria_escolhida.casefold()
        ]
        _avisar_linhas_invalidas(qtd_invalidas)
        _imprimir_tabela(
            filtrados,
            com_favorito=True,
            numerado=False,
            msg_vazia="Nenhum livro encontrado para esta categoria.",
        )
        input("")
        _limpar_tela()
        return


def listaAutor():
    """Lista livros de Livros.csv filtrados pelo nome (ou parte do nome) do autor."""
    print(f"{separador}\n{menuListaAutor}\n{separador}\n")
    print(f"{vermelho}Voltar{fimCor} => 0")

    _, validos, qtd_invalidas = _carregar_linhas_arquivo(arquivoLivros, com_favorito=True)
    nome_autor = _ler_texto_obrigatorio("Nome do Autor: ")
    _limpar_tela()

    if nome_autor == "0":
        return

    print(f"{separador}\n{menuListaAutor}\n{separador}\n")
    termo = nome_autor.casefold()
    filtrados = [
        (campos, valor)
        for _, campos, valor in validos
        if termo in campos[3].casefold()
    ]
    _avisar_linhas_invalidas(qtd_invalidas)
    _imprimir_tabela(
        filtrados,
        com_favorito=True,
        numerado=False,
        msg_vazia="Nenhum livro encontrado para este autor.",
    )
    input("")
    _limpar_tela()


def listaFavoritos():
    """Lista apenas os livros marcados como favoritos em Livros.csv."""
    print(f"{separador}\n{menuListaFav}\n{separador}\n")

    _, validos, qtd_invalidas = _carregar_linhas_arquivo(arquivoLivros, com_favorito=True)
    filtrados = [(campos, valor) for _, campos, valor in validos if campos[1] == "★"]
    _avisar_linhas_invalidas(qtd_invalidas)
    _imprimir_tabela(
        filtrados,
        com_favorito=True,
        numerado=False,
        msg_vazia="Nenhum livro favorito cadastrado.",
    )
    input("")
    _limpar_tela()


def _mover_para_meus_livros(linhas_brutas, idx_bruto, campos, valor):
    """Move um livro da Lista de Desejos para Meus Livros solicitando se é favorito."""
    _limpar_tela()
    favorito = _ler_favorito()
    if favorito is None:
        return False

    nome, categoria, autor = campos
    _adicionar_registro(arquivoLivros, [nome, favorito, categoria, autor], valor)
    del linhas_brutas[idx_bruto]
    _salvar_linhas_brutas(arquivoListaDesejo, linhas_brutas)

    _limpar_tela()
    print(f"{verde}Livro movido para Meus Livros!{fimCor}\nPressione {vermelho}(Enter){fimCor}")
    input()
    _limpar_tela()
    return True


def _gerenciar_lista(caminho, com_favorito=True, msg_vazia="Nenhum livro cadastrado."):
    """Exibe lista completa numerada e permite alterar, deletar ou mover desejos."""
    while True:
        linhas_brutas, validos, qtd_invalidas = _carregar_linhas_arquivo(
            caminho, com_favorito=com_favorito
        )
        registros = [(campos, valor) for _, campos, valor in validos]

        print()
        _avisar_linhas_invalidas(qtd_invalidas)
        _imprimir_tabela(registros, com_favorito=com_favorito, numerado=True, msg_vazia=msg_vazia)
        print()

        if not validos:
            input("")
            _limpar_tela()
            return

        print(f"Linhas editáveis [{amarelo}1{fimCor}] até [{amarelo}{len(validos)}{fimCor}].")
        editar_livro = input("Número da linha => ").strip()
        if not editar_livro.isdigit():
            _limpar_tela()
            return

        indice = int(editar_livro) - 1
        if indice < 0 or indice >= len(validos):
            _limpar_tela()
            return

        idx_bruto, campos, valor = validos[indice]
        _limpar_tela()

        if com_favorito:
            resumo = "| {:<20} | {:^6} | {:^18} | {:^18} | R${:>9,.2f}".format(
                _truncar(campos[0], 20),
                campos[1],
                _truncar(campos[2], 18),
                _truncar(campos[3], 18),
                valor,
            )
        else:
            resumo = "| {:<20} | {:^18} | {:^18} | R${:>9,.2f}".format(
                _truncar(campos[0], 20),
                _truncar(campos[1], 18),
                _truncar(campos[2], 18),
                valor,
            )

        borda_resumo = f"{azul}={fimCor}" * len(resumo)
        print(borda_resumo)
        print(resumo)
        print(borda_resumo)

        if com_favorito:
            print("\n1- Alterar \n2- Deletar \n0- Voltar\n")
        else:
            print("\n1- Alterar \n2- Deletar \n3- Mover para Meus Livros \n0- Voltar\n")
        op_alterar = input("Opção: ").strip()

        if op_alterar == "1":
            _limpar_tela()
            print(separador)
            novo_nome = _ler_texto_obrigatorio(
                f"\nNome do Livro [{campos[0]}] (Enter para manter): ",
                atual=campos[0],
            )
            _limpar_tela()

            novo_favorito = None
            if com_favorito:
                novo_favorito = _ler_favorito(atual=campos[1])
                if novo_favorito is None:
                    continue
                _limpar_tela()
                cat_atual = campos[2]
                autor_atual = campos[3]
            else:
                cat_atual = campos[1]
                autor_atual = campos[2]

            nova_cat = _escolher_categoria(atual=cat_atual)
            novo_autor = _ler_texto_obrigatorio(
                f"Nome do autor [{autor_atual}] (Enter para manter): ",
                atual=autor_atual,
            )
            _limpar_tela()

            novo_valor = _ler_preco(
                f"Valor do livro [{valor:.2f}] (Enter para manter): ",
                atual=valor,
            )
            if novo_valor is None:
                continue

            novos_campos = (
                [novo_nome, novo_favorito, nova_cat, novo_autor]
                if com_favorito
                else [novo_nome, nova_cat, novo_autor]
            )
            linhas_brutas[idx_bruto] = _formatar_linha_csv(novos_campos, novo_valor)
            _salvar_linhas_brutas(caminho, linhas_brutas)

            print(f"Livro atualizado!\nPressione {vermelho}(Enter){fimCor}")
            input()
            _limpar_tela()

        elif op_alterar == "2":
            confirmar = input(
                f'Tem certeza que deseja deletar "{campos[0]}"? (S/N): '
            ).strip().casefold()
            if confirmar not in ("s", "sim"):
                _limpar_tela()
                print(f"Exclusão cancelada.\nPressione {vermelho}(Enter){fimCor}")
                input()
                _limpar_tela()
                continue

            del linhas_brutas[idx_bruto]
            _salvar_linhas_brutas(caminho, linhas_brutas)
            _limpar_tela()
            print(f"Livro deletado!\nPressione {vermelho}(Enter){fimCor}")
            input()
            _limpar_tela()

        elif op_alterar == "3" and not com_favorito:
            _mover_para_meus_livros(linhas_brutas, idx_bruto, campos, valor)

        elif op_alterar == "0":
            _limpar_tela()
            return

        else:
            _limpar_tela()
            input(f"Opção inválida!\nPressione {vermelho}(Enter){fimCor}.")
            _limpar_tela()


def alterar():
    """Exibe todos os livros adquiridos e permite alteração ou exclusão."""
    _gerenciar_lista(arquivoLivros, com_favorito=True, msg_vazia="Nenhum livro cadastrado.")


def listaDesejos():
    """Exibe e gerencia o submenu Lista de Desejos."""
    while True:
        print(f"{separador}\n{menuListaDj}\n{separador}")
        print("1- Novo Livro\n2- Desejados\n0- Voltar")
        print("=-=" * 8)

        op = input("Opção: ").strip()
        _limpar_tela()

        if op == "1":
            livroDesejados()
        elif op == "2":
            exibirEditar()
        elif op == "0":
            return
        else:
            print(f"{vermelho}Opção inválida!{fimCor}\nPressione {vermelho}(Enter){fimCor}.")
            input()
            _limpar_tela()


def livroDesejados():
    """Cadastra um novo livro na Lista de Desejos."""
    _cadastrar_item(arquivoListaDesejo, com_favorito=False)


def exibirEditar():
    """Exibe todos os livros da Lista de Desejos e permite alteração, exclusão ou movimentação."""
    _gerenciar_lista(
        arquivoListaDesejo,
        com_favorito=False,
        msg_vazia="Nenhum livro na lista de desejos.",
    )


def startar():
    """Tela inicial da aplicação."""
    _limpar_tela()
    print(f"{separador}\n{menuStarte}\n{separador}")
    input("")
    _limpar_tela()
    principalMenu()


if __name__ == "__main__":
    import sys

    if "--gui" in sys.argv:
        from Interface import iniciar_interface

        iniciar_interface()
    else:
        startar()
