import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

import Biblioteca
import Interface


class InterfaceTestCase(unittest.TestCase):
    def setUp(self):
        self._orig_livros = Biblioteca.arquivoLivros
        self._orig_cats = Biblioteca.arquivoCategorias
        self._orig_desejos = Biblioteca.arquivoListaDesejo
        self._orig_capas = Biblioteca.pastaCapas
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

        Biblioteca.arquivoLivros = os.path.join(self.tmp_dir.name, "Arquivos", "Livros.csv")
        Biblioteca.arquivoCategorias = os.path.join(self.tmp_dir.name, "Arquivos", "Categorias.csv")
        Biblioteca.arquivoListaDesejo = os.path.join(self.tmp_dir.name, "Arquivos", "ListaDesejos.csv")
        Biblioteca.pastaCapas = os.path.join(self.tmp_dir.name, "Arquivos", "Capas")
        os.makedirs(os.path.dirname(Biblioteca.arquivoLivros), exist_ok=True)
        with open(Biblioteca.arquivoCategorias, "w", encoding="utf-8") as f:
            f.write("Ficção\nRomance\n")
        Biblioteca._adicionar_registro(
            Biblioteca.arquivoLivros,
            ["Duna", "★", "Ficção", "Frank Herbert"],
            79.90,
        )
        Biblioteca._adicionar_registro(
            Biblioteca.arquivoLivros,
            ["Dom Casmurro", "~", "Romance", "Machado de Assis"],
            39.90,
        )
        Biblioteca._adicionar_registro(
            Biblioteca.arquivoListaDesejo,
            ["1984", "Ficção", "George Orwell"],
            44.90,
        )

    def tearDown(self):
        Biblioteca.arquivoLivros = self._orig_livros
        Biblioteca.arquivoCategorias = self._orig_cats
        Biblioteca.arquivoListaDesejo = self._orig_desejos
        Biblioteca.pastaCapas = self._orig_capas

    def test_validar_preco_e_filtros(self):
        self.assertEqual(Interface._validar_preco_texto("49,90"), 49.9)
        self.assertEqual(Interface._validar_preco_texto("10.556"), 10.56)
        self.assertIsNone(Interface._validar_preco_texto("-1"))
        self.assertIsNone(Interface._validar_preco_texto("nan"))
        self.assertIsNone(Interface._validar_preco_texto("abc"))
        self.assertIsNone(Interface._validar_preco_texto(""))

        _, validos, _ = Biblioteca._carregar_linhas_arquivo(Biblioteca.arquivoLivros, com_favorito=True)
        res_fav = Interface._filtrar_registros(validos, True, apenas_favoritos=True)
        self.assertEqual(len(res_fav), 1)
        self.assertEqual(res_fav[0][1][0], "Duna")

        res_autor = Interface._filtrar_registros(validos, True, termo="machado")
        self.assertEqual(len(res_autor), 1)
        self.assertEqual(res_autor[0][1][0], "Dom Casmurro")

        res_cat = Interface._filtrar_registros(validos, True, categoria="romance")
        self.assertEqual(len(res_cat), 1)

    def test_app_tkinter_inicializa_menus_colunas_ordenacao_e_favorito(self):
        app = Interface.BibliotecaApp()
        try:
            app.withdraw()
            app.update_idletasks()
            # Inicia na página de Boas-Vindas
            self.assertEqual(app.tela_atual, "boas_vindas")
            self.assertEqual(app.lbl_boas_vindas_topo.cget("text"), "Seja bem vindo")
            self.assertEqual(app.lbl_boas_vindas_titulo.cget("text"), "à Biblioteca de Livros")

            # Vai para Meus Livros
            app.ir_para("livros")
            app.update_idletasks()
            self.assertEqual(app.tela_atual, "livros")
            self.assertEqual(len(app.itens_visiveis), 2)
            self.assertEqual(app.lbl_kpi_qtd.cget("text"), "2")
            self.assertEqual(app.lbl_kpi_valor.cget("text"), "R$ 119.80")
            self.assertEqual(app.lbl_kpi_extra_valor.cget("text"), "1")

            # Verifica remoção do botão Encerrar e recolher/estender com ícones gráficos
            self.assertFalse(hasattr(app, "btn_nav_encerrar"))
            self.assertFalse(app.sidebar_retraida)
            self.assertEqual(str(app.btn_toggle_sidebar.cget("image")), str(app.icone_retrair))
            app.alternar_sidebar()
            app.update_idletasks()
            self.assertTrue(app.sidebar_retraida)
            self.assertEqual(str(app.btn_toggle_sidebar.cget("image")), str(app.icone_estender))
            self.assertEqual(int(app.sidebar.cget("width")), Interface.LARGURA_SIDEBAR_RETRAIDA)
            self.assertFalse(app.corpo_sidebar.winfo_ismapped())
            app.alternar_sidebar()
            app.update_idletasks()
            self.assertFalse(app.sidebar_retraida)
            self.assertEqual(str(app.btn_toggle_sidebar.cget("image")), str(app.icone_retrair))
            self.assertEqual(int(app.sidebar.cget("width")), Interface.LARGURA_SIDEBAR_ABERTA)

            # Verifica Autor e Valor centralizados e coluna extra depois de Valor
            colunas = list(app.tree.cget("columns"))
            self.assertEqual(colunas[-2:], ["valor", "espaco"])
            self.assertEqual(str(app.tree.column("autor", "anchor")), "center")
            self.assertEqual(str(app.tree.column("valor", "anchor")), "center")

            # Ordenação por Valor crescente e decrescente
            app._ordenar_por_coluna("valor")
            self.assertEqual([c[1][0] for c in app.itens_visiveis], ["Dom Casmurro", "Duna"])
            app._ordenar_por_coluna("valor")
            self.assertEqual([c[1][0] for c in app.itens_visiveis], ["Duna", "Dom Casmurro"])

            # Alternar favorito no primeiro item (Duna: ★ -> ~)
            app.tree.selection_set("0")
            app.alternar_favorito_selecionado()
            regs = Biblioteca._carregar_registros(Biblioteca.arquivoLivros, com_favorito=True)
            duna = [r for r in regs if r[0][0] == "Duna"][0]
            self.assertEqual(duna[0][1], "~")

            # Vai para Lista de Desejos (verifica coluna extra após Valor e centralização)
            app.ir_para("desejos")
            app.update_idletasks()
            self.assertEqual(len(app.itens_visiveis), 1)
            self.assertEqual(app.lbl_kpi_valor.cget("text"), "R$ 44.90")
            self.assertEqual(list(app.tree.cget("columns"))[-2:], ["valor", "espaco"])
            self.assertEqual(str(app.tree.column("autor", "anchor")), "center")
            self.assertEqual(str(app.tree.column("valor", "anchor")), "center")

            # Vai para Como Usar, verifica bind/hover do título "Biblioteca" + linha e retorna para Boas-Vindas
            app.ir_para("como_usar")
            app.update_idletasks()
            self.assertEqual(app.tela_atual, "como_usar")
            self.assertTrue(app.lbl_titulo_biblioteca.bind("<Button-1>"))
            self.assertTrue(app.linha_titulo_biblioteca.bind("<Button-1>"))
            app._atualizar_hover_titulo(True)
            self.assertEqual(app.lbl_titulo_biblioteca.cget("fg"), Interface.PALETA["texto_suave"])
            self.assertEqual(app.linha_titulo_biblioteca.cget("bg"), Interface.PALETA["texto_suave"])
            app._atualizar_hover_titulo(False)
            self.assertEqual(app.lbl_titulo_biblioteca.cget("fg"), Interface.PALETA["texto_creme"])
            self.assertEqual(app.linha_titulo_biblioteca.cget("bg"), Interface.PALETA["acento_suave"])
            app.ir_para("boas_vindas")
            app.update_idletasks()
            self.assertEqual(app.tela_atual, "boas_vindas")

            dlg = Interface.DialogoCategorias(app)
            dlg.update_idletasks()
            self.assertEqual(dlg.lbl_total_cats.cget("text"), "2 categorias")
            self.assertEqual(len(dlg.tree_cats.get_children()), 2)
            self.assertLessEqual(dlg.winfo_reqheight(), 680)
            self.assertGreater(dlg.entrada_nova.winfo_reqheight(), 0)
            self.assertGreater(dlg.btn_adicionar_cat.winfo_reqheight(), 0)
            self.assertGreater(dlg.btn_editar_cat.winfo_reqheight(), 0)
            self.assertGreater(dlg.btn_deletar_cat.winfo_reqheight(), 0)
            dlg.destroy()
        finally:
            app.destroy()

    def test_dialogo_livro_com_imagem_lado_direito(self):
        img_exemplo = os.path.join(WORKSPACE, "Arquivos", "Imagens", "Tabela.png")
        self.assertTrue(os.path.exists(img_exemplo))

        app = Interface.BibliotecaApp()
        try:
            app.withdraw()
            dlg = Interface.DialogoLivro(app, com_favorito=True)
            try:
                dlg.update_idletasks()
                # Coluna esquerda e coluna direita existem e têm mesma configuração uniforme
                self.assertGreater(dlg.col_esquerda.winfo_reqheight(), 0)
                self.assertGreater(dlg.box_capa.winfo_reqheight(), 0)

                # Selecionar imagem, preencher dados e confirmar
                dlg._definir_imagem_selecionada(img_exemplo)
                self.assertIsNotNone(dlg._photo_capa)

                # Testar imagem vertical (capa retrato pequena): deve ampliar quase até as bordas superior e inferior
                capa_retrato = os.path.join(self.tmp_dir.name, "retrato.png")
                img_tmp = Interface.tk.PhotoImage(width=100, height=160)
                img_tmp.put("{#286451}", to=(0, 0, 100, 160))
                img_tmp.write(capa_retrato, format="png")
                dlg._definir_imagem_selecionada(capa_retrato)
                self.assertIsNotNone(dlg._photo_capa)
                alvo_w, alvo_h = dlg._dimensoes_area_capa()
                self.assertGreaterEqual(dlg._photo_capa.height(), alvo_h - 5)

                dlg.var_nome.set("Duna Ilustrado")
                dlg.var_fav.set(True)
                dlg.var_cat.set("Ficção")
                dlg.var_autor.set("Frank Herbert")
                dlg.var_valor.set("89,90")
                dlg._confirmar()

                self.assertIsNotNone(dlg.resultado)
                campos, valor, capa_nome = dlg.resultado
                self.assertEqual(campos, ["Duna Ilustrado", "★", "Ficção", "Frank Herbert"])
                self.assertEqual(valor, 89.90)
                self.assertTrue(capa_nome.endswith(".png"))
                self.assertTrue(os.path.exists(os.path.join(Biblioteca.pastaCapas, capa_nome)))

                # Salvar no CSV e validar persistência + preservação ao alternar favorito
                Biblioteca._adicionar_registro(Biblioteca.arquivoLivros, campos, valor, capa=capa_nome)
                linhas, validos, _ = Biblioteca._carregar_linhas_arquivo(Biblioteca.arquivoLivros, True)
                self.assertEqual(Biblioteca._extrair_capa_linha(linhas[-1], True), capa_nome)

                app.ir_para("livros")
                idx_ultimo = str(len(app.itens_visiveis) - 1)
                app.tree.selection_set(idx_ultimo)
                app.alternar_favorito_selecionado()
                linhas_apos, _, _ = Biblioteca._carregar_linhas_arquivo(Biblioteca.arquivoLivros, True)
                self.assertEqual(Biblioteca._extrair_capa_linha(linhas_apos[-1], True), capa_nome)
            finally:
                if dlg.winfo_exists():
                    dlg.destroy()

            # Testar remoção de imagem na edição
            dlg_edit = Interface.DialogoLivro(
                app,
                com_favorito=True,
                dados_iniciais=("Duna Ilustrado", "~", "Ficção", "Frank Herbert", 89.90),
                capa_inicial=capa_nome,
            )
            try:
                dlg_edit.update_idletasks()
                self.assertIsNotNone(dlg_edit._photo_capa)
                dlg_edit._remover_imagem()
                self.assertIsNone(dlg_edit._photo_capa)
                dlg_edit._confirmar()
                self.assertEqual(dlg_edit.resultado[2], "")
            finally:
                if dlg_edit.winfo_exists():
                    dlg_edit.destroy()
        finally:
            app.destroy()

    def test_dialogo_categorias_paginacao_e_crud_categorias(self):
        # Testar helpers de edição e exclusão de categoria (com preservação de linhas malformadas)
        with open(Biblioteca.arquivoLivros, "a", encoding="utf-8") as f:
            f.write("LinhaCorrompida\n")

        self.assertEqual(Biblioteca._contar_livros_por_categoria("Ficção"), 2)
        ok_dup, _ = Biblioteca._editar_categoria("Ficção", "romance")
        self.assertFalse(ok_dup)

        ok_edit, novo_nome = Biblioteca._editar_categoria("Ficção", "Ficção Científica")
        self.assertTrue(ok_edit)
        self.assertEqual(novo_nome, "Ficção Científica")
        self.assertIn("Ficção Científica", Biblioteca._ler_categorias())
        self.assertNotIn("Ficção", Biblioteca._ler_categorias())

        # Verifica cascata em Livros.csv e ListaDesejos.csv + preservação da linha malformada
        linhas_l, livros_v, inv_l = Biblioteca._carregar_linhas_arquivo(Biblioteca.arquivoLivros, True)
        self.assertEqual(inv_l, 1)
        self.assertIn("LinhaCorrompida\n", linhas_l)
        self.assertEqual(livros_v[0][1][2], "Ficção Científica")

        _, desejos_v, _ = Biblioteca._carregar_linhas_arquivo(Biblioteca.arquivoListaDesejo, False)
        self.assertEqual(desejos_v[0][1][1], "Ficção Científica")

        self.assertTrue(Biblioteca._deletar_categoria("Romance"))
        self.assertNotIn("Romance", Biblioteca._ler_categorias())

        # Gerar 65 categorias e testar paginação (20, 30, 40, 60)
        with open(Biblioteca.arquivoCategorias, "w", encoding="utf-8") as f:
            for i in range(1, 66):
                f.write(f"Categoria {i:02d}\n")

        app = Interface.BibliotecaApp()
        try:
            app.withdraw()
            dlg = Interface.DialogoCategorias(app)
            try:
                dlg.update()
                # Padrão: 20 por página -> 4 páginas
                self.assertEqual(dlg.por_pagina, 20)
                self.assertEqual(dlg.total_paginas, 4)
                self.assertEqual(dlg.lbl_pagina.cget("text"), "Página 1 de 4")
                self.assertEqual(len(dlg.tree_cats.get_children()), 20)

                dlg._pagina_proxima()
                dlg._pagina_proxima()
                dlg._pagina_proxima()
                self.assertEqual(dlg.pagina_atual, 4)
                self.assertEqual(len(dlg.tree_cats.get_children()), 5)

                # Mudar para 30 por página -> 3 páginas
                dlg.definir_por_pagina(30)
                self.assertEqual(dlg.total_paginas, 3)
                self.assertEqual(dlg.pagina_atual, 1)
                self.assertEqual(len(dlg.tree_cats.get_children()), 30)

                # Mudar para 40 por página -> 2 páginas
                dlg.definir_por_pagina(40)
                self.assertEqual(dlg.total_paginas, 2)
                self.assertEqual(len(dlg.tree_cats.get_children()), 40)
                dlg._pagina_proxima()
                self.assertEqual(len(dlg.tree_cats.get_children()), 25)

                # Mudar para 60 por página -> 2 páginas
                dlg.definir_por_pagina(60)
                self.assertEqual(dlg.total_paginas, 2)
                self.assertEqual(len(dlg.tree_cats.get_children()), 60)
                dlg._pagina_proxima()
                self.assertEqual(len(dlg.tree_cats.get_children()), 5)

                # Adicionar nova categoria via entrada -> total 66, permanece visível
                dlg.var_nova.set("Categoria Extra")
                dlg._adicionar()
                self.assertEqual(dlg.lbl_total_cats.cget("text"), "66 categorias")
                self.assertIn("Categoria Extra", dlg.categorias_pagina)
            finally:
                dlg.destroy()
        finally:
            app.destroy()


class BibliotecaTestCase(unittest.TestCase):
    def setUp(self):
        self._orig_livros = Biblioteca.arquivoLivros
        self._orig_cats = Biblioteca.arquivoCategorias
        self._orig_desejos = Biblioteca.arquivoListaDesejo
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

        Biblioteca.arquivoLivros = os.path.join(self.tmp_dir.name, "Arquivos", "Livros.csv")
        Biblioteca.arquivoCategorias = os.path.join(self.tmp_dir.name, "Arquivos", "Categorias.csv")
        Biblioteca.arquivoListaDesejo = os.path.join(self.tmp_dir.name, "Arquivos", "ListaDesejos.csv")

    def tearDown(self):
        Biblioteca.arquivoLivros = self._orig_livros
        Biblioteca.arquivoCategorias = self._orig_cats
        Biblioteca.arquivoListaDesejo = self._orig_desejos

    def _run(self, func, inputs):
        it = iter(inputs)
        printed = []
        with patch("builtins.input", side_effect=lambda *args: next(it)):
            with patch("os.system"):
                with patch("builtins.print", side_effect=lambda *args, **kwargs: printed.append(" ".join(map(str, args)))):
                    func()
        return "\n".join(printed)

    def test_arquivos_ausentes_e_vazios_com_mensagens(self):
        out_alt = self._run(Biblioteca.alterar, [""])
        self.assertIn("Nenhum livro cadastrado.", out_alt)

        out_des = self._run(Biblioteca.exibirEditar, [""])
        self.assertIn("Nenhum livro na lista de desejos.", out_des)

        out_fav = self._run(Biblioteca.listaFavoritos, [""])
        self.assertIn("Nenhum livro favorito cadastrado.", out_fav)

        out_aut = self._run(Biblioteca.listaAutor, ["Fulano", ""])
        self.assertIn("Nenhum livro encontrado para este autor.", out_aut)

        self._run(Biblioteca.listaCategoria, ["0"])

    def test_preserva_linhas_malformadas_ao_editar_e_deletar(self):
        os.makedirs(os.path.dirname(Biblioteca.arquivoLivros), exist_ok=True)
        with open(Biblioteca.arquivoCategorias, "w", encoding="utf-8") as f:
            f.write("Ficção\n")
        with open(Biblioteca.arquivoLivros, "w", encoding="utf-8") as f:
            f.write(
                "LinhaCorrompida\n"
                "Duna,★,Ficção,Frank Herbert,79.90\n"
                "ValorRuim,★,Ficção,Autor,abc\n"
                "1984,~,Ficção,George Orwell,44.90\n"
            )

        # Editar o primeiro livro válido (Duna -> Enter mantém tudo exceto preço) e sair
        out = self._run(Biblioteca.alterar, ["1", "1", "", "", "", "", "85,00", "", ""])
        self.assertIn("2 linha(s) malformada(s)", out)

        with open(Biblioteca.arquivoLivros, encoding="utf-8") as f:
            conteudo = f.read()
        self.assertIn("LinhaCorrompida\n", conteudo)
        self.assertIn("ValorRuim,★,Ficção,Autor,abc\n", conteudo)
        self.assertIn("Duna,★,Ficção,Frank Herbert,85.00\n", conteudo)
        self.assertIn("1984,~,Ficção,George Orwell,44.90\n", conteudo)

        # Deletar o segundo livro válido (1984) com confirmação 's'
        self._run(Biblioteca.alterar, ["2", "2", "s", "", ""])
        with open(Biblioteca.arquivoLivros, encoding="utf-8") as f:
            conteudo_apos_del = f.read()
        self.assertIn("LinhaCorrompida\n", conteudo_apos_del)
        self.assertIn("ValorRuim,★,Ficção,Autor,abc\n", conteudo_apos_del)
        self.assertIn("Duna,★,Ficção,Frank Herbert,85.00\n", conteudo_apos_del)
        self.assertNotIn("1984,~,Ficção,George Orwell,44.90\n", conteudo_apos_del)

    def test_confirmacao_cancelamento_exclusao(self):
        os.makedirs(os.path.dirname(Biblioteca.arquivoLivros), exist_ok=True)
        Biblioteca._adicionar_registro(
            Biblioteca.arquivoLivros,
            ["Dom Casmurro", "★", "Romance", "Machado de Assis"],
            39.90,
        )

        out = self._run(Biblioteca.alterar, ["1", "2", "n", "", ""])
        self.assertIn("Exclusão cancelada.", out)
        regs = Biblioteca._carregar_registros(Biblioteca.arquivoLivros, com_favorito=True)
        self.assertEqual(len(regs), 1)

    def test_edicao_parcial_mantem_valores_com_enter(self):
        os.makedirs(os.path.dirname(Biblioteca.arquivoLivros), exist_ok=True)
        with open(Biblioteca.arquivoCategorias, "w", encoding="utf-8") as f:
            f.write("Romance\n")
        Biblioteca._adicionar_registro(
            Biblioteca.arquivoLivros,
            ["Dom Casmurro", "★", "Romance", "Machado de Assis"],
            39.90,
        )

        # Alterar apenas o título e manter favorito, categoria, autor e preço com Enter
        self._run(Biblioteca.alterar, ["1", "1", "Dom Casmurro (Ed. Luxo)", "", "", "", "", "", ""])
        regs = Biblioteca._carregar_registros(Biblioteca.arquivoLivros, com_favorito=True)
        self.assertEqual(
            regs,
            [(["Dom Casmurro (Ed. Luxo)", "★", "Romance", "Machado de Assis"], 39.90)],
        )

    def test_mover_lista_desejos_para_meus_livros(self):
        os.makedirs(os.path.dirname(Biblioteca.arquivoListaDesejo), exist_ok=True)
        Biblioteca._adicionar_registro(
            Biblioteca.arquivoListaDesejo,
            ["Duna", "Ficção", "Frank Herbert"],
            79.90,
        )

        # Opção inválida em favorito NÃO deve remover da lista de desejos
        self._run(Biblioteca.exibirEditar, ["1", "3", "9", "", ""])
        self.assertEqual(len(Biblioteca._carregar_registros(Biblioteca.arquivoListaDesejo, False)), 1)
        self.assertEqual(len(Biblioteca._carregar_registros(Biblioteca.arquivoLivros, True)), 0)

        # Mover escolhendo favorito "1" (Sim)
        out = self._run(Biblioteca.exibirEditar, ["1", "3", "1", "", ""])
        self.assertIn("Livro movido para Meus Livros!", out)
        self.assertEqual(len(Biblioteca._carregar_registros(Biblioteca.arquivoListaDesejo, False)), 0)
        self.assertEqual(
            Biblioteca._carregar_registros(Biblioteca.arquivoLivros, True),
            [(["Duna", "★", "Ficção", "Frank Herbert"], 79.90)],
        )

    def test_cadastro_com_virgulas_e_preco_com_virgula(self):
        os.makedirs(os.path.dirname(Biblioteca.arquivoCategorias), exist_ok=True)
        with open(Biblioteca.arquivoCategorias, "w", encoding="utf-8") as f:
            f.write("Ficção")

        self._run(
            Biblioteca.novoLivro,
            [
                "", "O Senhor dos Anéis, Vol. 1",
                "1",
                "ficção",
                "J. R. R. Tolkien, Jr.",
                "129,955",
                "",
            ],
        )
        regs = Biblioteca._carregar_registros(Biblioteca.arquivoLivros, True)
        self.assertEqual(
            regs,
            [(["O Senhor dos Anéis, Vol. 1", "★", "Ficção", "J. R. R. Tolkien, Jr."], 129.96)],
        )
        self.assertEqual(Biblioteca._ler_categorias(), ["Ficção"])

    def test_busca_categoria_e_autor_flexivel(self):
        os.makedirs(os.path.dirname(Biblioteca.arquivoCategorias), exist_ok=True)
        with open(Biblioteca.arquivoCategorias, "w", encoding="utf-8") as f:
            f.write("Ficção\n")
        Biblioteca._adicionar_registro(
            Biblioteca.arquivoLivros,
            ["Duna", "★", "Ficção", "Frank Herbert"],
            79.90,
        )

        out_cat = self._run(Biblioteca.listaCategoria, ["ficção", ""])
        self.assertIn("Duna", out_cat)

        out_aut = self._run(Biblioteca.listaAutor, ["herbert", ""])
        self.assertIn("Duna", out_aut)

    def test_execucao_cli_de_outro_diretorio(self):
        with tempfile.TemporaryDirectory() as other_cwd:
            script = os.path.join(WORKSPACE, "Biblioteca.py")
            proc = subprocess.run(
                [sys.executable, script],
                cwd=other_cwd,
                input="\n3\n\n2\n9\n\n0\n0\n",
                text=True,
                capture_output=True,
                encoding="utf-8",
                timeout=10,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("COMO USAR", proc.stdout)
            self.assertIn("PROGRAMA FINALIZADO!", proc.stdout)

    def test_arquivos_padrao_do_repositorio_integros(self):
        _, livros, inv_l = Biblioteca._carregar_linhas_arquivo(self._orig_livros, com_favorito=True)
        _, desejos, inv_d = Biblioteca._carregar_linhas_arquivo(self._orig_desejos, com_favorito=False)
        self.assertEqual(inv_l, 0)
        self.assertEqual(inv_d, 0)
        self.assertGreater(len(livros), 0)
        self.assertGreater(len(desejos), 0)


if __name__ == "__main__":
    unittest.main()
