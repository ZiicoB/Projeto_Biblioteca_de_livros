import math
import os
import shutil
import subprocess
import tempfile
import tkinter as tk
import uuid
from tkinter import filedialog, messagebox, ttk

import Biblioteca

# Paleta de cores fornecida pelo usuário
PALETA = {
    "bg_principal": "#071B18",   # Fundo profundo
    "bg_card": "#123C35",        # Cards, painéis e linhas alternadas
    "acento": "#286451",         # Botões principais, abas ativas e cabeçalho
    "acento_suave": "#638B72",   # Hover, bordas e botões secundários
    "texto_suave": "#B8C8A7",    # Subtítulos e rótulos secundários
    "texto_creme": "#F4EAD8",    # Texto principal e destaques quentes
    "perigo": "#7A3632",         # Botão de exclusão harmonizado
    "perigo_hover": "#93423D",
}

LARGURA_SIDEBAR_ABERTA = 235
LARGURA_SIDEBAR_RETRAIDA = 48

FONTE_TITULO = ("Segoe UI", 18, "bold")
FONTE_SUBTITULO = ("Segoe UI", 10)
FONTE_CARD_LABEL = ("Segoe UI", 9, "bold")
FONTE_CARD_VALOR = ("Segoe UI", 15, "bold")
FONTE_BOTAO = ("Segoe UI", 10, "bold")
FONTE_MENU = ("Segoe UI", 10, "bold")
FONTE_PADRAO = ("Segoe UI", 10)
FONTE_TABELA = ("Segoe UI", 10)
FONTE_CABECALHO = ("Segoe UI", 10, "bold")


def _hex_para_rgb(cor_hex):
    """Converte '#RRGGBB' para tupla (r, g, b)."""
    cor = cor_hex.lstrip("#")
    return tuple(int(cor[i : i + 2], 16) for i in (0, 2, 4))


def _dist_segmento(px, py, x1, y1, x2, y2):
    """Distância euclidiana mínima do ponto (px, py) ao segmento (x1,y1)-(x2,y2)."""
    dx = x2 - x1
    dy = y2 - y1
    comp2 = dx * dx + dy * dy
    if comp2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / comp2))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _criar_icone_seta_parede(retrair, bg_hex, fg_hex="#F4EAD8", tamanho=22):
    """Gera um ícone suavizado (anti-aliased) de seta com parede para retrair/estender."""
    bg_rgb = _hex_para_rgb(bg_hex)
    fg_rgb = _hex_para_rgb(fg_hex)

    # Parede à esquerda + seta apontando para a parede (retrair) ou para fora (estender)
    segmentos = [(4.5, 4.5, 4.5, 16.5)]
    if retrair:
        segmentos.extend([
            (17.5, 10.5, 8.5, 10.5),
            (12.5, 6.5, 8.5, 10.5),
            (12.5, 14.5, 8.5, 10.5),
        ])
    else:
        segmentos.extend([
            (8.0, 10.5, 17.5, 10.5),
            (13.5, 6.5, 17.5, 10.5),
            (13.5, 14.5, 17.5, 10.5),
        ])

    raio = 0.95
    linhas_pixels = []
    for y in range(tamanho):
        linha = []
        for x in range(tamanho):
            dist = min(_dist_segmento(x + 0.5, y + 0.5, *seg) for seg in segmentos)
            alpha = max(0.0, min(1.0, (raio + 0.65 - dist) / 1.15))
            r = int(bg_rgb[0] * (1.0 - alpha) + fg_rgb[0] * alpha)
            g = int(bg_rgb[1] * (1.0 - alpha) + fg_rgb[1] * alpha)
            b = int(bg_rgb[2] * (1.0 - alpha) + fg_rgb[2] * alpha)
            linha.append(f"#{r:02x}{g:02x}{b:02x}")
        linhas_pixels.append("{" + " ".join(linha) + "}")

    img = tk.PhotoImage(width=tamanho, height=tamanho)
    img.put(" ".join(linhas_pixels))
    return img


def _centralizar_janela(janela, largura, altura, pai=None):
    """Centraliza uma janela na tela ou sobre a janela pai."""
    janela.update_idletasks()
    if pai is not None:
        x = pai.winfo_rootx() + max(0, (pai.winfo_width() - largura) // 2)
        y = pai.winfo_rooty() + max(0, (pai.winfo_height() - altura) // 2)
    else:
        x = max(0, (janela.winfo_screenwidth() - largura) // 2)
        y = max(0, (janela.winfo_screenheight() - altura) // 2)
    janela.geometry(f"{largura}x{altura}+{x}+{y}")


def _criar_botao(parent, texto, comando, bg, fg, hover_bg, padx=14, pady=8, anchor="center", font=FONTE_BOTAO):
    """Cria um botão flat estilizado com efeito hover."""
    btn = tk.Button(
        parent,
        text=texto,
        command=comando,
        bg=bg,
        fg=fg,
        activebackground=hover_bg,
        activeforeground=fg,
        relief="flat",
        bd=0,
        cursor="hand2",
        font=font,
        padx=padx,
        pady=pady,
        anchor=anchor,
    )
    btn.bind("<Enter>", lambda _e: btn.configure(bg=hover_bg) if btn["state"] == "normal" else None)
    btn.bind("<Leave>", lambda _e: btn.configure(bg=bg) if btn["state"] == "normal" else None)
    return btn


def _validar_preco_texto(bruto):
    """Valida string de preço (aceita vírgula ou ponto, >= 0 e finito)."""
    texto = bruto.strip().replace(",", ".")
    if not texto:
        return None
    try:
        valor = float(texto)
    except ValueError:
        return None
    if not math.isfinite(valor) or valor < 0:
        return None
    return round(valor, 2)


def _filtrar_registros(validos, com_favorito, termo="", categoria="Todas", apenas_favoritos=False):
    """Filtra registros carregados por termo (título/autor), categoria e favorito."""
    termo_norm = termo.strip().casefold()
    cat_norm = categoria.strip().casefold()
    filtrados = []

    for idx_bruto, campos, valor in validos:
        if com_favorito:
            nome, favorito, cat, autor = campos
            if apenas_favoritos and favorito != "★":
                continue
        else:
            nome, cat, autor = campos

        if cat_norm and cat_norm != "todas" and cat.casefold() != cat_norm:
            continue
        if termo_norm and termo_norm not in nome.casefold() and termo_norm not in autor.casefold():
            continue

        filtrados.append((idx_bruto, campos, valor))

    return filtrados


def _ordenar_itens(itens, coluna, reverso, com_favorito):
    """Ordena a lista de itens visíveis pela coluna escolhida."""
    if coluna == "num":
        return list(reversed(itens)) if reverso else list(itens)

    def chave(item):
        _idx, campos, valor = item
        if com_favorito:
            nome, fav, cat, autor = campos
        else:
            nome, cat, autor = campos
            fav = ""

        if coluna == "titulo":
            return nome.casefold()
        if coluna == "fav":
            return 0 if fav == "★" else 1
        if coluna == "categoria":
            return cat.casefold()
        if coluna == "autor":
            return autor.casefold()
        if coluna == "valor":
            return valor
        return nome.casefold()

    return sorted(itens, key=chave, reverse=reverso)


def _resolver_caminho_capa(capa_ref):
    """Resolve o caminho completo da imagem de capa (relativo a pastaCapas ou absoluto)."""
    ref = (capa_ref or "").strip()
    if not ref:
        return ""
    if os.path.isabs(ref):
        return ref
    return os.path.join(Biblioteca.pastaCapas, ref)


def _converter_para_png_redimensionado(origem, destino, max_w=340, max_h=340, permitir_ampliar=True):
    """Converte e redimensiona uma imagem para PNG mantendo proporção (Windows/fallback)."""
    if not os.path.exists(origem):
        return False

    if os.name == "nt":
        ps_script = (
            "Add-Type -AssemblyName System.Drawing; "
            "$src=$env:CAPA_SRC; $dst=$env:CAPA_DST; "
            "$mw=[int]$env:CAPA_W; $mh=[int]$env:CAPA_H; "
            "$amp=$env:CAPA_AMP -eq '1'; "
            "$img=[System.Drawing.Image]::FromFile($src); "
            "$ratio=[Math]::Min($mw/$img.Width, $mh/$img.Height); "
            "if(-not $amp -and $ratio -gt 1){$ratio=1}; "
            "$nw=[Math]::Max(1,[int][Math]::Round($img.Width*$ratio)); "
            "$nh=[Math]::Max(1,[int][Math]::Round($img.Height*$ratio)); "
            "$bmp=New-Object System.Drawing.Bitmap($nw,$nh); "
            "$g=[System.Drawing.Graphics]::FromImage($bmp); "
            "$g.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic; "
            "$g.DrawImage($img,0,0,$nw,$nh); "
            "$bmp.Save($dst,[System.Drawing.Imaging.ImageFormat]::Png); "
            "$g.Dispose(); $bmp.Dispose(); $img.Dispose()"
        )
        env = {
            **os.environ,
            "CAPA_SRC": os.path.abspath(origem),
            "CAPA_DST": os.path.abspath(destino),
            "CAPA_W": str(max_w),
            "CAPA_H": str(max_h),
            "CAPA_AMP": "1" if permitir_ampliar else "0",
        }
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            env=env,
            capture_output=True,
            text=True,
            creationflags=flags,
            timeout=15,
        )
        if res.returncode == 0 and os.path.exists(destino):
            return True

    ext = os.path.splitext(origem)[1].lower()
    if ext in (".png", ".gif", ".ppm"):
        shutil.copy2(origem, destino)
        return True
    return False


def _carregar_photoimage_capa(caminho, max_w=340, max_h=340):
    """Carrega uma imagem em tk.PhotoImage ajustando escala se necessário."""
    if not caminho or not os.path.exists(caminho):
        return None
    try:
        img = tk.PhotoImage(file=caminho)
    except tk.TclError:
        return None

    w, h = img.width(), img.height()
    if w > max_w or h > max_h:
        fator = max(math.ceil(w / max_w), math.ceil(h / max_h))
        if fator > 1:
            img = img.subsample(fator, fator)
    return img


def _salvar_capa_definitiva(caminho_origem, max_w=340, max_h=340):
    """Salva uma cópia redimensionada em Arquivos/Capas e retorna o nome do arquivo."""
    os.makedirs(Biblioteca.pastaCapas, exist_ok=True)
    nome_arquivo = f"capa_{uuid.uuid4().hex[:10]}.png"
    destino = os.path.join(Biblioteca.pastaCapas, nome_arquivo)
    if _converter_para_png_redimensionado(caminho_origem, destino, max_w=max_w, max_h=max_h):
        return nome_arquivo
    return ""


class DialogoLivro(tk.Toplevel):
    """Modal estilizado para cadastro e edição de livros com área lateral para capa."""

    def __init__(self, pai, com_favorito=True, dados_iniciais=None, capa_inicial=""):
        super().__init__(pai)
        self.resultado = None
        self.com_favorito = com_favorito
        self.editando = dados_iniciais is not None

        self._capa_atual = (capa_inicial or "").strip()
        self._nova_imagem_origem = ""
        self._capa_removida = False
        self._temp_preview = ""
        self._photo_capa = None

        titulo_janela = "Editar Livro" if self.editando else "Novo Livro"
        self.title(titulo_janela)
        self.configure(bg=PALETA["bg_principal"])
        self.minsize(740, 480)
        self.transient(pai)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        container = tk.Frame(
            self,
            bg=PALETA["bg_card"],
            padx=22,
            pady=20,
            highlightthickness=1,
            highlightbackground=PALETA["acento"],
        )
        container.pack(fill="both", expand=True, padx=14, pady=14)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        tk.Label(
            container,
            text=titulo_janela,
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        if dados_iniciais is not None:
            if com_favorito:
                nome_ini, fav_ini, cat_ini, autor_ini, valor_ini = dados_iniciais
            else:
                nome_ini, cat_ini, autor_ini, valor_ini = dados_iniciais
                fav_ini = "~"
            valor_str = f"{valor_ini:.2f}"
        else:
            nome_ini, fav_ini, cat_ini, autor_ini, valor_str = "", "~", "", "", ""

        self.var_nome = tk.StringVar(value=nome_ini)
        self.var_fav = tk.BooleanVar(value=(fav_ini == "★"))
        self.var_cat = tk.StringVar(value=cat_ini)
        self.var_autor = tk.StringVar(value=autor_ini)
        self.var_valor = tk.StringVar(value=valor_str)

        # Grade com duas colunas de mesmo tamanho (formulário à esquerda, imagem à direita)
        grade = tk.Frame(container, bg=PALETA["bg_card"])
        grade.grid(row=1, column=0, sticky="nsew")
        grade.columnconfigure(0, weight=1, uniform="col_livro")
        grade.columnconfigure(1, weight=1, uniform="col_livro")
        grade.rowconfigure(0, weight=1)

        # Coluna esquerda: dados do livro
        self.col_esquerda = tk.Frame(grade, bg=PALETA["bg_card"])
        self.col_esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.entry_nome = self._campo_texto(self.col_esquerda, "Título do Livro", self.var_nome)

        if com_favorito:
            chk = tk.Checkbutton(
                self.col_esquerda,
                text="Marcar como Favorito (★)",
                variable=self.var_fav,
                bg=PALETA["bg_card"],
                fg=PALETA["texto_creme"],
                selectcolor=PALETA["bg_principal"],
                activebackground=PALETA["bg_card"],
                activeforeground=PALETA["texto_creme"],
                font=FONTE_PADRAO,
                cursor="hand2",
            )
            chk.pack(anchor="w", pady=(2, 10))

        tk.Label(
            self.col_esquerda,
            text="Categoria (escolha ou digite uma nova)",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_suave"],
            font=FONTE_CARD_LABEL,
        ).pack(anchor="w")
        categorias = Biblioteca._ler_categorias()
        self.combo_cat = ttk.Combobox(
            self.col_esquerda,
            textvariable=self.var_cat,
            values=categorias,
            font=FONTE_PADRAO,
            style="Biblioteca.TCombobox",
        )
        self.combo_cat.pack(fill="x", pady=(4, 10), ipady=4)

        self._campo_texto(self.col_esquerda, "Autor", self.var_autor)
        self._campo_texto(self.col_esquerda, "Valor (R$)", self.var_valor, pady_bottom=0)

        # Coluna direita (mesmo tamanho): área opcional da imagem do livro
        self.col_direita = tk.Frame(grade, bg=PALETA["bg_card"])
        self.col_direita.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        self.col_direita.columnconfigure(0, weight=1)
        self.col_direita.rowconfigure(1, weight=1)

        tk.Label(
            self.col_direita,
            text="Capa do Livro (Opcional)",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_suave"],
            font=FONTE_CARD_LABEL,
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.box_capa = tk.Frame(
            self.col_direita,
            bg=PALETA["bg_principal"],
            highlightthickness=1,
            highlightbackground=PALETA["acento_suave"],
            cursor="hand2",
        )
        self.box_capa.grid(row=1, column=0, sticky="nsew")
        self.box_capa.pack_propagate(False)

        self.lbl_preview_capa = tk.Label(
            self.box_capa,
            text="",
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_suave"],
            font=FONTE_PADRAO,
            justify="center",
            cursor="hand2",
        )
        self.lbl_preview_capa.pack(fill="both", expand=True, padx=3, pady=3)
        self.box_capa.bind("<Button-1>", lambda _e: self._escolher_imagem())
        self.lbl_preview_capa.bind("<Button-1>", lambda _e: self._escolher_imagem())

        acoes_capa = tk.Frame(self.col_direita, bg=PALETA["bg_card"])
        acoes_capa.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        self.btn_escolher_capa = _criar_botao(
            acoes_capa,
            "Escolher Imagem",
            self._escolher_imagem,
            bg=PALETA["acento"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["acento_suave"],
            padx=12,
            pady=6,
        )
        self.btn_escolher_capa.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_remover_capa = _criar_botao(
            acoes_capa,
            "Remover",
            self._remover_imagem,
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_suave"],
            hover_bg=PALETA["perigo_hover"],
            padx=10,
            pady=6,
        )
        self.btn_remover_capa.pack(side="right")

        # Rodapé principal (Cancelar / Salvar)
        botoes = tk.Frame(container, bg=PALETA["bg_card"])
        botoes.grid(row=2, column=0, sticky="ew", pady=(16, 0))

        btn_salvar = _criar_botao(
            botoes,
            "Salvar",
            self._confirmar,
            bg=PALETA["acento"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["acento_suave"],
        )
        btn_salvar.pack(side="right", padx=(8, 0))

        btn_cancelar = _criar_botao(
            botoes,
            "Cancelar",
            self.destroy,
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_suave"],
            hover_bg=PALETA["acento_suave"],
        )
        btn_cancelar.pack(side="right")

        self.bind("<Return>", lambda _e: self._confirmar())
        self.bind("<Escape>", lambda _e: self.destroy())

        altura = 500 if com_favorito else 460
        _centralizar_janela(self, 780, altura, pai=pai)
        self.update_idletasks()
        self._atualizar_preview_capa(_resolver_caminho_capa(self._capa_atual))
        self.entry_nome.focus_set()

    def destroy(self):
        self._limpar_temp_preview()
        super().destroy()

    def _limpar_temp_preview(self):
        if self._temp_preview and os.path.exists(self._temp_preview):
            try:
                os.remove(self._temp_preview)
            except OSError:
                pass
        self._temp_preview = ""

    def _escolher_imagem(self):
        caminho = filedialog.askopenfilename(
            parent=self,
            title="Selecionar imagem da capa",
            filetypes=[
                ("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not caminho:
            return
        self._definir_imagem_selecionada(caminho)

    def _dimensoes_area_capa(self):
        """Retorna largura e altura úteis da caixa de capa (quase encostando nas bordas)."""
        self.update_idletasks()
        w = self.box_capa.winfo_width()
        h = self.box_capa.winfo_height()
        if w < 80:
            w = 340
        if h < 80:
            h = 330 if self.com_favorito else 290
        return max(120, w - 8), max(120, h - 8)

    def _definir_imagem_selecionada(self, caminho):
        """Define o caminho de imagem escolhido pelo usuário e atualiza a pré-visualização."""
        self._limpar_temp_preview()
        alvo_w, alvo_h = self._dimensoes_area_capa()
        fd, temp_png = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        if _converter_para_png_redimensionado(caminho, temp_png, max_w=alvo_w, max_h=alvo_h):
            self._temp_preview = temp_png
            self._nova_imagem_origem = caminho
            self._capa_removida = False
            self._atualizar_preview_capa(temp_png)
        else:
            if os.path.exists(temp_png):
                os.remove(temp_png)
            messagebox.showwarning(
                "Imagem não suportada",
                "Não foi possível carregar essa imagem. Tente um arquivo PNG, JPG, GIF ou BMP.",
                parent=self,
            )

    def _remover_imagem(self):
        self._limpar_temp_preview()
        self._nova_imagem_origem = ""
        self._capa_removida = True
        self._atualizar_preview_capa("")

    def _atualizar_preview_capa(self, caminho):
        alvo_w, alvo_h = self._dimensoes_area_capa()
        img = None
        if caminho and os.path.exists(caminho):
            img = _carregar_photoimage_capa(caminho, max_w=alvo_w, max_h=alvo_h)
            if img is not None and img.width() < alvo_w * 0.85 and img.height() < alvo_h * 0.85:
                # Re-escala uma capa já salva menor para preencher até perto das bordas
                fd, temp_png = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                if _converter_para_png_redimensionado(caminho, temp_png, max_w=alvo_w, max_h=alvo_h):
                    self._limpar_temp_preview()
                    self._temp_preview = temp_png
                    img = _carregar_photoimage_capa(temp_png, max_w=alvo_w, max_h=alvo_h)
                elif os.path.exists(temp_png):
                    os.remove(temp_png)

        if img is not None:
            self._photo_capa = img
            self.lbl_preview_capa.configure(image=self._photo_capa, text="")
            self.btn_remover_capa.configure(state="normal")
        else:
            self._photo_capa = None
            self.lbl_preview_capa.configure(
                image="",
                text=(
                    "Nenhuma imagem selecionada\n\n"
                    "Clique aqui ou em 'Escolher Imagem'\n"
                    "para adicionar a capa do livro\n"
                    "(PNG, JPG, GIF, BMP)"
                ),
            )
            self.btn_remover_capa.configure(state="disabled")

    def _campo_texto(self, parent, rotulo, var, pady_bottom=10):
        tk.Label(
            parent,
            text=rotulo,
            bg=PALETA["bg_card"],
            fg=PALETA["texto_suave"],
            font=FONTE_CARD_LABEL,
        ).pack(anchor="w")
        entrada = tk.Entry(
            parent,
            textvariable=var,
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_creme"],
            insertbackground=PALETA["texto_creme"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=PALETA["acento_suave"],
            highlightcolor=PALETA["texto_creme"],
            font=FONTE_PADRAO,
        )
        entrada.pack(fill="x", pady=(4, pady_bottom), ipady=6)
        return entrada

    def _confirmar(self):
        nome = self.var_nome.get().strip()
        categoria = self.var_cat.get().strip()
        autor = self.var_autor.get().strip()
        valor = _validar_preco_texto(self.var_valor.get())

        if not nome or not categoria or not autor:
            messagebox.showwarning("Campos obrigatórios", "Preencha Título, Categoria e Autor.", parent=self)
            return
        if valor is None:
            messagebox.showwarning("Valor inválido", "Informe um valor numérico válido (>= 0).", parent=self)
            return

        if self._nova_imagem_origem:
            alvo_w, alvo_h = self._dimensoes_area_capa()
            capa_final = _salvar_capa_definitiva(self._nova_imagem_origem, max_w=alvo_w, max_h=alvo_h)
        elif self._capa_removida:
            capa_final = ""
        else:
            capa_final = self._capa_atual

        categoria_final = Biblioteca._adicionar_categoria(categoria)
        if self.com_favorito:
            favorito = "★" if self.var_fav.get() else "~"
            self.resultado = ([nome, favorito, categoria_final, autor], valor, capa_final)
        else:
            self.resultado = ([nome, categoria_final, autor], valor, capa_final)
        self.destroy()


class DialogoEditarCategoria(tk.Toplevel):
    """Modal estilizado para renomear uma categoria existente."""

    def __init__(self, pai, nome_atual):
        super().__init__(pai)
        self.resultado = None
        self.title("Editar Categoria")
        self.configure(bg=PALETA["bg_principal"])
        self.resizable(False, False)
        self.transient(pai)
        self.grab_set()

        card = tk.Frame(
            self,
            bg=PALETA["bg_card"],
            padx=22,
            pady=18,
            highlightthickness=1,
            highlightbackground=PALETA["acento"],
        )
        card.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(
            card,
            text="Editar Categoria",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        tk.Label(
            card,
            text="Novo nome da categoria",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_suave"],
            font=FONTE_CARD_LABEL,
        ).pack(anchor="w")

        self.var_nome = tk.StringVar(value=nome_atual)
        entrada = tk.Entry(
            card,
            textvariable=self.var_nome,
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_creme"],
            insertbackground=PALETA["texto_creme"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=PALETA["acento_suave"],
            highlightcolor=PALETA["texto_creme"],
            font=FONTE_PADRAO,
        )
        entrada.pack(fill="x", pady=(6, 14), ipady=6)

        botoes = tk.Frame(card, bg=PALETA["bg_card"])
        botoes.pack(fill="x")

        _criar_botao(
            botoes,
            "Salvar",
            self._confirmar,
            bg=PALETA["acento"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["acento_suave"],
        ).pack(side="right", padx=(8, 0))

        _criar_botao(
            botoes,
            "Cancelar",
            self.destroy,
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_suave"],
            hover_bg=PALETA["acento_suave"],
        ).pack(side="right")

        self.bind("<Return>", lambda _e: self._confirmar())
        self.bind("<Escape>", lambda _e: self.destroy())
        _centralizar_janela(self, 390, 210, pai=pai)
        entrada.select_range(0, tk.END)
        entrada.focus_set()

    def _confirmar(self):
        nome = self.var_nome.get().strip()
        if not nome:
            messagebox.showwarning("Atenção", "O nome da categoria não pode ficar vazio.", parent=self)
            return
        self.resultado = nome
        self.destroy()


class DialogoCategorias(tk.Toplevel):
    """Modal amplo com paginação configurável para criar, editar e deletar categorias."""

    OPCOES_POR_PAGINA = (20, 30, 40, 60)

    def __init__(self, pai):
        super().__init__(pai)
        self.title("Categorias Cadastradas")
        self.configure(bg=PALETA["bg_principal"])
        self.minsize(640, 620)
        self.transient(pai)
        self.grab_set()

        self.por_pagina = 20
        self.pagina_atual = 1
        self.total_paginas = 1
        self.categorias_pagina = []

        card = tk.Frame(
            self,
            bg=PALETA["bg_card"],
            padx=22,
            pady=18,
            highlightthickness=1,
            highlightbackground=PALETA["acento"],
        )
        card.pack(fill="both", expand=True, padx=14, pady=14)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        # Linha 0: Cabeçalho
        topo = tk.Frame(card, bg=PALETA["bg_card"])
        topo.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        tk.Label(
            topo,
            text="Categorias Cadastradas",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            font=("Segoe UI", 15, "bold"),
        ).pack(side="left")

        self.lbl_total_cats = tk.Label(
            topo,
            text="0 categorias",
            bg=PALETA["acento"],
            fg=PALETA["texto_creme"],
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
        )
        self.lbl_total_cats.pack(side="right")

        # Linha 1: Controles de paginação e quantidade por página (20, 30, 40, 60)
        barra_pag = tk.Frame(card, bg=PALETA["bg_card"])
        barra_pag.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        tk.Label(
            barra_pag,
            text="Exibir:",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_suave"],
            font=FONTE_CARD_LABEL,
        ).pack(side="left", padx=(0, 8))

        self.btn_por_pagina = tk.Menubutton(
            barra_pag,
            text="20 por página ▾",
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_creme"],
            activebackground=PALETA["acento_suave"],
            activeforeground=PALETA["texto_creme"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=FONTE_BOTAO,
            padx=12,
            pady=6,
            indicatoron=False,
        )
        menu_qtd = tk.Menu(
            self.btn_por_pagina,
            tearoff=0,
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            activebackground=PALETA["acento"],
            activeforeground=PALETA["texto_creme"],
            font=FONTE_PADRAO,
        )
        for qtd in self.OPCOES_POR_PAGINA:
            menu_qtd.add_command(
                label=f"{qtd} por página",
                command=lambda q=qtd: self.definir_por_pagina(q),
            )
        self.btn_por_pagina.configure(menu=menu_qtd)
        self.btn_por_pagina.pack(side="left")

        nav_pag = tk.Frame(barra_pag, bg=PALETA["bg_card"])
        nav_pag.pack(side="right")

        self.btn_pag_anterior = _criar_botao(
            nav_pag,
            "◀ Anterior",
            self._pagina_anterior,
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["acento_suave"],
            padx=10,
            pady=5,
        )
        self.btn_pag_anterior.pack(side="left")

        self.lbl_pagina = tk.Label(
            nav_pag,
            text="Página 1 de 1",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            font=FONTE_CARD_LABEL,
            padx=12,
        )
        self.lbl_pagina.pack(side="left")

        self.btn_pag_proxima = _criar_botao(
            nav_pag,
            "Próxima ▶",
            self._pagina_proxima,
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["acento_suave"],
            padx=10,
            pady=5,
        )
        self.btn_pag_proxima.pack(side="left")

        # Linha 2: Tabela expansível de categorias
        tabela_cats_box = tk.Frame(
            card,
            bg=PALETA["bg_principal"],
            padx=1,
            pady=1,
            highlightthickness=1,
            highlightbackground=PALETA["acento_suave"],
        )
        tabela_cats_box.grid(row=2, column=0, sticky="nsew", pady=(0, 12))

        self.tree_cats = ttk.Treeview(
            tabela_cats_box,
            columns=("num", "categoria"),
            show="headings",
            style="Biblioteca.Treeview",
            height=8,
            selectmode="browse",
        )
        self.tree_cats.heading("num", text="#")
        self.tree_cats.heading("categoria", text="Nome da Categoria")
        self.tree_cats.column("num", width=65, anchor="center", stretch=False)
        self.tree_cats.column("categoria", width=520, anchor="w", stretch=True)

        scroll = ttk.Scrollbar(
            tabela_cats_box,
            orient="vertical",
            command=self.tree_cats.yview,
            style="Biblioteca.Vertical.TScrollbar",
        )
        self.tree_cats.configure(yscrollcommand=scroll.set)
        self.tree_cats.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree_cats.tag_configure("par", background=PALETA["bg_card"], foreground=PALETA["texto_creme"])
        self.tree_cats.tag_configure("impar", background=PALETA["bg_principal"], foreground=PALETA["texto_creme"])
        self.tree_cats.bind("<Double-1>", lambda _e: self._editar_selecionada())

        # Linha 3: Adicionar Nova Categoria (sempre visível)
        add_box = tk.Frame(
            card,
            bg=PALETA["bg_principal"],
            padx=14,
            pady=12,
            highlightthickness=1,
            highlightbackground=PALETA["acento"],
        )
        add_box.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        tk.Label(
            add_box,
            text="Adicionar Nova Categoria",
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_suave"],
            font=FONTE_CARD_LABEL,
        ).pack(anchor="w")

        linha_add = tk.Frame(add_box, bg=PALETA["bg_principal"])
        linha_add.pack(fill="x", pady=(6, 0))

        self.var_nova = tk.StringVar()
        self.entrada_nova = tk.Entry(
            linha_add,
            textvariable=self.var_nova,
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            insertbackground=PALETA["texto_creme"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=PALETA["acento_suave"],
            highlightcolor=PALETA["texto_creme"],
            font=FONTE_PADRAO,
        )
        self.entrada_nova.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 10))

        self.btn_adicionar_cat = _criar_botao(
            linha_add,
            "+ Adicionar Categoria",
            self._adicionar,
            bg=PALETA["acento"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["acento_suave"],
            padx=16,
            pady=7,
        )
        self.btn_adicionar_cat.pack(side="right")

        # Linha 4: Editar, Deletar e Fechar
        rodape = tk.Frame(card, bg=PALETA["bg_card"])
        rodape.grid(row=4, column=0, sticky="ew")

        self.btn_editar_cat = _criar_botao(
            rodape,
            "Editar Categoria",
            self._editar_selecionada,
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["acento_suave"],
        )
        self.btn_editar_cat.pack(side="left", padx=(0, 8))

        self.btn_deletar_cat = _criar_botao(
            rodape,
            "Deletar Categoria",
            self._deletar_selecionada,
            bg=PALETA["perigo"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["perigo_hover"],
        )
        self.btn_deletar_cat.pack(side="left")

        _criar_botao(
            rodape,
            "Fechar",
            self.destroy,
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_suave"],
            hover_bg=PALETA["acento_suave"],
        ).pack(side="right")

        self.entrada_nova.bind("<Return>", lambda _e: self._adicionar())
        self.bind("<Escape>", lambda _e: self.destroy())
        _centralizar_janela(self, 740, 680, pai=pai)
        self._atualizar_lista()
        self.entrada_nova.focus_set()

    def definir_por_pagina(self, quantidade):
        """Altera a quantidade exibida por página (20, 30, 40 ou 60) e reorganiza."""
        if quantidade not in self.OPCOES_POR_PAGINA:
            return
        self.por_pagina = quantidade
        self.pagina_atual = 1
        self.btn_por_pagina.configure(text=f"{quantidade} por página ▾")
        self._atualizar_lista()

    def _pagina_anterior(self):
        if self.pagina_atual > 1:
            self.pagina_atual -= 1
            self._atualizar_lista()

    def _pagina_proxima(self):
        if self.pagina_atual < self.total_paginas:
            self.pagina_atual += 1
            self._atualizar_lista()

    def _atualizar_lista(self):
        for item in self.tree_cats.get_children():
            self.tree_cats.delete(item)

        categorias = Biblioteca._ler_categorias()
        total = len(categorias)
        self.total_paginas = max(1, math.ceil(total / self.por_pagina))
        if self.pagina_atual > self.total_paginas:
            self.pagina_atual = self.total_paginas
        if self.pagina_atual < 1:
            self.pagina_atual = 1

        inicio = (self.pagina_atual - 1) * self.por_pagina
        fim = inicio + self.por_pagina
        self.categorias_pagina = categorias[inicio:fim]

        for offset, cat in enumerate(self.categorias_pagina):
            num_global = inicio + offset + 1
            tag = "par" if offset % 2 == 0 else "impar"
            self.tree_cats.insert("", "end", iid=str(offset), values=(num_global, f"  {cat}"), tags=(tag,))

        sufixo = "categoria" if total == 1 else "categorias"
        self.lbl_total_cats.configure(text=f"{total} {sufixo}")
        self.lbl_pagina.configure(text=f"Página {self.pagina_atual} de {self.total_paginas}")
        self.btn_pag_anterior.configure(state="normal" if self.pagina_atual > 1 else "disabled")
        self.btn_pag_proxima.configure(state="normal" if self.pagina_atual < self.total_paginas else "disabled")

    def _categoria_selecionada(self):
        selecao = self.tree_cats.selection()
        if not selecao:
            messagebox.showinfo("Seleção", "Selecione uma categoria na lista primeiro.", parent=self)
            return None
        return self.categorias_pagina[int(selecao[0])]

    def _adicionar(self):
        nome = self.var_nova.get().strip()
        if not nome:
            messagebox.showwarning("Atenção", "Digite o nome da categoria.", parent=self)
            return
        categorias_antes = Biblioteca._ler_categorias()
        existente = Biblioteca._buscar_categoria(nome, categorias_antes)
        if existente:
            messagebox.showinfo("Categoria existente", f'A categoria "{existente}" já está cadastrada.', parent=self)
            return

        Biblioteca._adicionar_categoria(nome)
        self.var_nova.set("")
        novo_total = len(Biblioteca._ler_categorias())
        self.pagina_atual = max(1, math.ceil(novo_total / self.por_pagina))
        self._atualizar_lista()

    def _editar_selecionada(self):
        cat_antiga = self._categoria_selecionada()
        if not cat_antiga:
            return
        dialogo = DialogoEditarCategoria(self, cat_antiga)
        self.wait_window(dialogo)
        if not dialogo.resultado:
            return

        ok, msg = Biblioteca._editar_categoria(cat_antiga, dialogo.resultado)
        if not ok:
            messagebox.showwarning("Não foi possível editar", msg, parent=self)
            return
        self._atualizar_lista()

    def _deletar_selecionada(self):
        cat = self._categoria_selecionada()
        if not cat:
            return
        qtd_livros = Biblioteca._contar_livros_por_categoria(cat)
        aviso_extra = (
            f"\n\nAviso: {qtd_livros} livro(s)/desejo(s) usam essa categoria atualmente."
            if qtd_livros > 0
            else ""
        )
        confirmar = messagebox.askyesno(
            "Confirmar exclusão",
            f'Tem certeza que deseja deletar a categoria "{cat}"?{aviso_extra}',
            parent=self,
        )
        if not confirmar:
            return

        Biblioteca._deletar_categoria(cat)
        self._atualizar_lista()


class BibliotecaApp(tk.Tk):
    """Aplicação gráfica principal da Biblioteca de Livros."""

    def __init__(self):
        super().__init__()
        self.title("Biblioteca de Livros")
        self.configure(bg=PALETA["bg_principal"])
        self.minsize(1040, 660)
        _centralizar_janela(self, 1180, 720)

        self.tela_atual = "boas_vindas"  # "boas_vindas" | "livros" | "desejos" | "como_usar"
        self.sidebar_retraida = False
        self.linhas_brutas = []
        self.todos_validos = []
        self.itens_visiveis = []
        self.qtd_invalidas = 0

        self.ordem_coluna = None
        self.ordem_reversa = False
        self._suprimir_trace = False

        self.var_busca = tk.StringVar()
        self.var_categoria = tk.StringVar(value="Todas")
        self.var_so_favoritos = tk.BooleanVar(value=False)

        self._configurar_estilos()
        self._construir_layout()
        self._configurar_atalhos()
        self.ir_para("boas_vindas")

    def _configurar_estilos(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "Biblioteca.Treeview",
            background=PALETA["bg_card"],
            foreground=PALETA["texto_creme"],
            fieldbackground=PALETA["bg_card"],
            borderwidth=0,
            rowheight=32,
            font=FONTE_TABELA,
        )
        style.map(
            "Biblioteca.Treeview",
            background=[("selected", PALETA["acento"])],
            foreground=[("selected", PALETA["texto_creme"])],
        )

        style.configure(
            "Biblioteca.Treeview.Heading",
            background=PALETA["acento"],
            foreground=PALETA["texto_creme"],
            relief="flat",
            borderwidth=1,
            bordercolor=PALETA["acento_suave"],
            font=FONTE_CABECALHO,
            padding=(8, 8),
        )
        style.map(
            "Biblioteca.Treeview.Heading",
            background=[("active", PALETA["acento_suave"])],
        )

        style.configure(
            "Biblioteca.Vertical.TScrollbar",
            background=PALETA["acento"],
            troughcolor=PALETA["bg_principal"],
            borderwidth=0,
            arrowcolor=PALETA["texto_creme"],
        )
        style.map(
            "Biblioteca.Vertical.TScrollbar",
            background=[("active", PALETA["acento_suave"])],
        )

        style.configure(
            "Biblioteca.TCombobox",
            fieldbackground=PALETA["bg_principal"],
            background=PALETA["acento"],
            foreground=PALETA["texto_creme"],
            arrowcolor=PALETA["texto_creme"],
            bordercolor=PALETA["acento_suave"],
            lightcolor=PALETA["acento_suave"],
            darkcolor=PALETA["bg_principal"],
        )
        style.map(
            "Biblioteca.TCombobox",
            fieldbackground=[("readonly", PALETA["bg_principal"])],
            foreground=[("readonly", PALETA["texto_creme"])],
            selectbackground=[("readonly", PALETA["acento"])],
            selectforeground=[("readonly", PALETA["texto_creme"])],
        )

        self.option_add("*TCombobox*Listbox.background", PALETA["bg_card"])
        self.option_add("*TCombobox*Listbox.foreground", PALETA["texto_creme"])
        self.option_add("*TCombobox*Listbox.selectBackground", PALETA["acento"])
        self.option_add("*TCombobox*Listbox.selectForeground", PALETA["texto_creme"])

    def _construir_layout(self):
        raiz = tk.Frame(self, bg=PALETA["bg_principal"])
        raiz.pack(fill="both", expand=True)

        # === SIDEBAR RETRÁTIL (MENU PRINCIPAL) ===
        self.sidebar = tk.Frame(
            raiz,
            bg=PALETA["bg_card"],
            width=LARGURA_SIDEBAR_ABERTA,
            highlightthickness=1,
            highlightbackground=PALETA["acento"],
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Ícones gráficos suavizados para retrair/estender a barra lateral
        self.icone_retrair = _criar_icone_seta_parede(True, PALETA["bg_principal"])
        self.icone_retrair_hover = _criar_icone_seta_parede(True, PALETA["acento_suave"])
        self.icone_estender = _criar_icone_seta_parede(False, PALETA["bg_principal"])
        self.icone_estender_hover = _criar_icone_seta_parede(False, PALETA["acento_suave"])

        # Barra superior da sidebar com botão de recolher / estender
        self.topo_sidebar = tk.Frame(self.sidebar, bg=PALETA["bg_card"], padx=10, pady=12)
        self.topo_sidebar.pack(fill="x")

        self.box_titulo_sidebar = tk.Frame(self.topo_sidebar, bg=PALETA["bg_card"], cursor="hand2")
        self.box_titulo_sidebar.pack(side="left", fill="x", expand=True)

        self.lbl_titulo_biblioteca = tk.Label(
            self.box_titulo_sidebar,
            text="Biblioteca",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            font=("Segoe UI", 16, "bold"),
            cursor="hand2",
        )
        self.lbl_titulo_biblioteca.pack(anchor="w")

        self.linha_titulo_biblioteca = tk.Frame(
            self.box_titulo_sidebar,
            bg=PALETA["acento_suave"],
            height=2,
            width=105,
            cursor="hand2",
        )
        self.linha_titulo_biblioteca.pack(anchor="w", pady=(1, 4))

        self.lbl_subtitulo_biblioteca = tk.Label(
            self.box_titulo_sidebar,
            text="Gerenciador de Livros",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_suave"],
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        self.lbl_subtitulo_biblioteca.pack(anchor="w")

        for widget_titulo in (
            self.box_titulo_sidebar,
            self.lbl_titulo_biblioteca,
            self.linha_titulo_biblioteca,
            self.lbl_subtitulo_biblioteca,
        ):
            widget_titulo.bind("<Button-1>", lambda _e: self.ir_para("boas_vindas"))
            widget_titulo.bind("<Enter>", lambda _e: self._atualizar_hover_titulo(True))
            widget_titulo.bind("<Leave>", lambda _e: self._atualizar_hover_titulo(False))

        self.btn_toggle_sidebar = tk.Button(
            self.topo_sidebar,
            image=self.icone_retrair,
            command=self.alternar_sidebar,
            bg=PALETA["bg_principal"],
            activebackground=PALETA["acento_suave"],
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=6,
            pady=6,
        )
        self.btn_toggle_sidebar.bind("<Enter>", lambda _e: self._atualizar_hover_toggle(True))
        self.btn_toggle_sidebar.bind("<Leave>", lambda _e: self._atualizar_hover_toggle(False))
        self.btn_toggle_sidebar.pack(side="right", anchor="n")

        # Corpo da sidebar (ocultado quando retraída)
        self.corpo_sidebar = tk.Frame(self.sidebar, bg=PALETA["bg_card"], padx=14, pady=4)
        self.corpo_sidebar.pack(fill="both", expand=True)

        tk.Frame(self.corpo_sidebar, bg=PALETA["acento"], height=1).pack(fill="x", pady=(0, 12))

        tk.Label(
            self.corpo_sidebar,
            text="MENU PRINCIPAL",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_suave"],
            font=FONTE_CARD_LABEL,
        ).pack(anchor="w", pady=(0, 6))

        self.btn_nav_livros = self._criar_botao_sidebar(
            self.corpo_sidebar, "1- Meus Livros", lambda: self.ir_para("livros")
        )
        self.btn_nav_desejos = self._criar_botao_sidebar(
            self.corpo_sidebar, "2- Lista de Desejos", lambda: self.ir_para("desejos")
        )
        self.btn_nav_como_usar = self._criar_botao_sidebar(
            self.corpo_sidebar, "3- Como Usar", lambda: self.ir_para("como_usar")
        )

        # === ÁREA DE CONTEÚDO ===
        self.area_conteudo = tk.Frame(raiz, bg=PALETA["bg_principal"])
        self.area_conteudo.pack(side="right", fill="both", expand=True)

        self._construir_tela_boas_vindas()
        self._construir_tela_lista()
        self._construir_tela_como_usar()

    def _criar_botao_sidebar(self, parent, texto, comando, bg_padrao=None, hover=None):
        bg = bg_padrao or PALETA["bg_principal"]
        hov = hover or PALETA["acento_suave"]
        btn = tk.Button(
            parent,
            text=texto,
            command=comando,
            bg=bg,
            fg=PALETA["texto_creme"],
            activebackground=hov,
            activeforeground=PALETA["texto_creme"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=FONTE_MENU,
            anchor="w",
            padx=12,
            pady=9,
        )
        btn.pack(fill="x", pady=4)
        btn._bg_base = bg
        btn._hover = hov
        btn.bind("<Enter>", lambda _e, b=btn: b.configure(bg=b._hover))
        btn.bind("<Leave>", lambda _e, b=btn: b.configure(bg=b._bg_base))
        return btn

    def _atualizar_hover_titulo(self, em_hover):
        """Atualiza a cor do título Biblioteca e da linha abaixo ao passar o mouse."""
        if em_hover:
            self.lbl_titulo_biblioteca.configure(fg=PALETA["texto_suave"])
            self.linha_titulo_biblioteca.configure(bg=PALETA["texto_suave"])
        else:
            self.lbl_titulo_biblioteca.configure(fg=PALETA["texto_creme"])
            self.linha_titulo_biblioteca.configure(bg=PALETA["acento_suave"])

    def _atualizar_hover_toggle(self, em_hover):
        """Atualiza fundo e ícone do botão de recolher/estender no hover."""
        if em_hover:
            icone = self.icone_estender_hover if self.sidebar_retraida else self.icone_retrair_hover
            bg = PALETA["acento_suave"]
        else:
            icone = self.icone_estender if self.sidebar_retraida else self.icone_retrair
            bg = PALETA["bg_principal"]
        self.btn_toggle_sidebar.configure(image=icone, bg=bg)

    def alternar_sidebar(self):
        """Retrai ou estende a barra lateral mantendo a coluna fina com o ícone no topo."""
        self.sidebar_retraida = not self.sidebar_retraida
        if self.sidebar_retraida:
            self.corpo_sidebar.pack_forget()
            self.box_titulo_sidebar.pack_forget()
            self.btn_toggle_sidebar.pack_forget()
            self.btn_toggle_sidebar.configure(image=self.icone_estender, bg=PALETA["bg_principal"])
            self.btn_toggle_sidebar.pack(anchor="center")
            self.sidebar.configure(width=LARGURA_SIDEBAR_RETRAIDA)
        else:
            self.sidebar.configure(width=LARGURA_SIDEBAR_ABERTA)
            self.btn_toggle_sidebar.pack_forget()
            self.box_titulo_sidebar.pack(side="left", fill="x", expand=True)
            self.btn_toggle_sidebar.configure(image=self.icone_retrair, bg=PALETA["bg_principal"])
            self.btn_toggle_sidebar.pack(side="right", anchor="n")
            self.corpo_sidebar.pack(fill="both", expand=True)

    def _construir_tela_boas_vindas(self):
        """Constrói a página inicial de boas-vindas do projeto."""
        self.frame_boas_vindas = tk.Frame(self.area_conteudo, bg=PALETA["bg_principal"], padx=32, pady=28)

        # Banner de topo: "Seja bem vindo" / "à Biblioteca de Livros"
        hero = tk.Frame(
            self.frame_boas_vindas,
            bg=PALETA["bg_card"],
            padx=26,
            pady=24,
            highlightthickness=1,
            highlightbackground=PALETA["acento"],
        )
        hero.pack(fill="x", pady=(0, 18))

        self.lbl_boas_vindas_topo = tk.Label(
            hero,
            text="Seja bem vindo",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_suave"],
            font=("Segoe UI", 14, "bold"),
        )
        self.lbl_boas_vindas_topo.pack(anchor="w")

        self.lbl_boas_vindas_titulo = tk.Label(
            hero,
            text="à Biblioteca de Livros",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            font=("Segoe UI", 26, "bold"),
        )
        self.lbl_boas_vindas_titulo.pack(anchor="w", pady=(2, 8))

        tk.Label(
            hero,
            text="Gerencie os livros que você já possui, organize favoritos, categorias e acompanhe sua lista de desejos em um só lugar.",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_suave"],
            font=FONTE_PADRAO,
            wraplength=760,
            justify="left",
        ).pack(anchor="w")

        # Cards de apresentação (Trabalho Facultativo + Linguagens Usadas)
        grid_info = tk.Frame(self.frame_boas_vindas, bg=PALETA["bg_principal"])
        grid_info.pack(fill="both", expand=True)
        grid_info.columnconfigure((0, 1), weight=1, uniform="info_home")
        grid_info.rowconfigure(0, weight=1)

        card_sobre = tk.Frame(
            grid_info,
            bg=PALETA["bg_card"],
            padx=22,
            pady=20,
            highlightthickness=1,
            highlightbackground=PALETA["acento"],
        )
        card_sobre.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(
            card_sobre,
            text="Sobre o Projeto",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        tk.Label(
            card_sobre,
            text=(
                "Este projeto foi criado por Adriano Barnard Medeiros como um trabalho "
                "facultativo (avaliativo) para a disciplina de Fundamentos da Programação.\n\n"
                "O objetivo é oferecer uma forma prática e visual de catalogar livros comprados, "
                "controlar gastos, marcar favoritos, anexar imagens de capa e planejar futuras leituras."
            ),
            bg=PALETA["bg_card"],
            fg=PALETA["texto_suave"],
            font=FONTE_PADRAO,
            wraplength=360,
            justify="left",
        ).pack(anchor="w", fill="both", expand=True)

        card_tech = tk.Frame(
            grid_info,
            bg=PALETA["bg_card"],
            padx=22,
            pady=20,
            highlightthickness=1,
            highlightbackground=PALETA["acento"],
        )
        card_tech.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        tk.Label(
            card_tech,
            text="Linguagens e Tecnologias Usadas",
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        tecnologias = [
            ("Python 3", "Lógica da aplicação, manipulação de arquivos e testes automatizados (unittest)."),
            ("Tkinter / ttk", "Interface gráfica nativa com paleta esmeralda e creme personalizada."),
            ("CSV", "Armazenamento local leve dos livros, lista de desejos e categorias."),
            ("PowerShell / .NET", "Conversão e redimensionamento das imagens de capa no Windows."),
        ]
        for nome_t, desc_t in tecnologias:
            linha_t = tk.Frame(card_tech, bg=PALETA["bg_principal"], padx=10, pady=7)
            linha_t.pack(fill="x", pady=4)
            tk.Label(
                linha_t,
                text=nome_t,
                bg=PALETA["bg_principal"],
                fg=PALETA["texto_creme"],
                font=FONTE_BOTAO,
            ).pack(anchor="w")
            tk.Label(
                linha_t,
                text=desc_t,
                bg=PALETA["bg_principal"],
                fg=PALETA["texto_suave"],
                font=("Segoe UI", 9),
                wraplength=330,
                justify="left",
            ).pack(anchor="w")

    def _construir_tela_lista(self):
        self.frame_lista = tk.Frame(self.area_conteudo, bg=PALETA["bg_principal"])

        # Cabeçalho da seção
        header = tk.Frame(self.frame_lista, bg=PALETA["bg_principal"], padx=24, pady=16)
        header.pack(fill="x")

        self.lbl_secao_titulo = tk.Label(
            header,
            text="Meus Livros",
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_creme"],
            font=FONTE_TITULO,
        )
        self.lbl_secao_titulo.pack(anchor="w")

        self.lbl_secao_subtitulo = tk.Label(
            header,
            text="Gerencie sua coleção de livros adquiridos",
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_suave"],
            font=FONTE_SUBTITULO,
        )
        self.lbl_secao_subtitulo.pack(anchor="w")

        tk.Frame(self.frame_lista, bg=PALETA["acento"], height=1).pack(fill="x", padx=24)

        # Cards de resumo (KPIs)
        cards_row = tk.Frame(self.frame_lista, bg=PALETA["bg_principal"], padx=24, pady=12)
        cards_row.pack(fill="x")
        cards_row.columnconfigure((0, 1, 2), weight=1, uniform="kpi")

        self.lbl_kpi_qtd = self._criar_card_kpi(cards_row, 0, "LIVROS EXIBIDOS", "0", padx=(0, 8))
        self.lbl_kpi_valor = self._criar_card_kpi(cards_row, 1, "VALOR TOTAL", "R$ 0.00", padx=(4, 4))
        self.lbl_kpi_extra_titulo, self.lbl_kpi_extra_valor = self._criar_card_kpi(
            cards_row, 2, "FAVORITOS", "0", retornar_titulo=True, padx=(8, 0)
        )

        # Barra de filtros
        filtros = tk.Frame(
            self.frame_lista,
            bg=PALETA["bg_card"],
            padx=14,
            pady=10,
            highlightthickness=1,
            highlightbackground=PALETA["acento"],
        )
        filtros.pack(fill="x", padx=24, pady=(0, 10))

        tk.Label(
            filtros, text="Buscar (Título/Autor):", bg=PALETA["bg_card"], fg=PALETA["texto_suave"], font=FONTE_CARD_LABEL
        ).pack(side="left")
        self.entry_busca = tk.Entry(
            filtros,
            textvariable=self.var_busca,
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_creme"],
            insertbackground=PALETA["texto_creme"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=PALETA["acento_suave"],
            highlightcolor=PALETA["texto_creme"],
            font=FONTE_PADRAO,
            width=22,
        )
        self.entry_busca.pack(side="left", padx=(8, 14), ipady=4)
        self.var_busca.trace_add(
            "write", lambda *_args: None if self._suprimir_trace else self.aplicar_filtros()
        )

        tk.Label(
            filtros, text="Categoria:", bg=PALETA["bg_card"], fg=PALETA["texto_suave"], font=FONTE_CARD_LABEL
        ).pack(side="left")
        self.combo_filtro_cat = ttk.Combobox(
            filtros,
            textvariable=self.var_categoria,
            state="readonly",
            width=16,
            font=FONTE_PADRAO,
            style="Biblioteca.TCombobox",
        )
        self.combo_filtro_cat.pack(side="left", padx=(8, 12), ipady=2)
        self.combo_filtro_cat.bind("<<ComboboxSelected>>", lambda _e: self.aplicar_filtros())

        self.chk_fav = tk.Checkbutton(
            filtros,
            text="Somente Favoritos (★)",
            variable=self.var_so_favoritos,
            command=self.aplicar_filtros,
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            selectcolor=PALETA["bg_principal"],
            activebackground=PALETA["bg_card"],
            activeforeground=PALETA["texto_creme"],
            font=FONTE_PADRAO,
            cursor="hand2",
        )
        self.chk_fav.pack(side="left", padx=(0, 8))

        _criar_botao(
            filtros,
            "Limpar",
            self._limpar_filtros,
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_suave"],
            hover_bg=PALETA["acento_suave"],
            padx=10,
            pady=4,
        ).pack(side="right")

        # Área da Tabela
        tabela_box = tk.Frame(
            self.frame_lista,
            bg=PALETA["bg_card"],
            padx=2,
            pady=2,
            highlightthickness=1,
            highlightbackground=PALETA["acento"],
        )
        tabela_box.pack(fill="both", expand=True, padx=24)

        self.tree = ttk.Treeview(
            tabela_box,
            style="Biblioteca.Treeview",
            show="headings",
            selectmode="browse",
        )
        scroll = ttk.Scrollbar(
            tabela_box,
            orient="vertical",
            command=self.tree.yview,
            style="Biblioteca.Vertical.TScrollbar",
        )
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.tag_configure("par", background=PALETA["bg_card"], foreground=PALETA["texto_creme"])
        self.tree.tag_configure("impar", background=PALETA["bg_principal"], foreground=PALETA["texto_creme"])
        self.tree.bind("<Double-1>", lambda _e: self.editar_selecionado())

        # Barra de aviso / dica
        self.lbl_aviso = tk.Label(
            self.frame_lista,
            text="",
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_suave"],
            font=("Segoe UI", 9),
        )
        self.lbl_aviso.pack(anchor="w", padx=24, pady=(6, 0))

        # Barra de ações inferior
        acoes = tk.Frame(self.frame_lista, bg=PALETA["bg_principal"], padx=24, pady=12)
        acoes.pack(fill="x")

        _criar_botao(
            acoes,
            "+ Novo Livro",
            self.adicionar_livro,
            bg=PALETA["acento"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["acento_suave"],
        ).pack(side="left", padx=(0, 8))

        _criar_botao(
            acoes,
            "Editar",
            self.editar_selecionado,
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["acento_suave"],
        ).pack(side="left", padx=(0, 8))

        self.btn_favoritar = _criar_botao(
            acoes,
            "Favoritar / Desfavoritar",
            self.alternar_favorito_selecionado,
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["acento_suave"],
        )

        _criar_botao(
            acoes,
            "Deletar",
            self.deletar_selecionado,
            bg=PALETA["perigo"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["perigo_hover"],
        ).pack(side="left", padx=(0, 8))

        self.btn_mover = _criar_botao(
            acoes,
            "Mover para Meus Livros",
            self.mover_selecionado,
            bg=PALETA["acento"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["acento_suave"],
        )

        _criar_botao(
            acoes,
            "Criar Categoria",
            self.gerenciar_categorias,
            bg=PALETA["bg_card"],
            fg=PALETA["texto_suave"],
            hover_bg=PALETA["acento_suave"],
        ).pack(side="right")

    def _construir_tela_como_usar(self):
        self.frame_como_usar = tk.Frame(self.area_conteudo, bg=PALETA["bg_principal"], padx=28, pady=22)

        topo = tk.Frame(self.frame_como_usar, bg=PALETA["bg_principal"])
        topo.pack(fill="x", pady=(0, 12))

        tk.Label(
            topo,
            text="Como Usar o Programa",
            bg=PALETA["bg_principal"],
            fg=PALETA["texto_creme"],
            font=FONTE_TITULO,
        ).pack(side="left")

        _criar_botao(
            topo,
            "Voltar para Meus Livros",
            lambda: self.ir_para("livros"),
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            hover_bg=PALETA["acento_suave"],
            pady=6,
        ).pack(side="right")

        tk.Frame(self.frame_como_usar, bg=PALETA["acento"], height=1).pack(fill="x", pady=(0, 14))

        guia_box = tk.Frame(
            self.frame_como_usar,
            bg=PALETA["bg_card"],
            padx=22,
            pady=18,
            highlightthickness=1,
            highlightbackground=PALETA["acento"],
        )
        guia_box.pack(fill="both", expand=True)

        texto_guia = tk.Text(
            guia_box,
            bg=PALETA["bg_card"],
            fg=PALETA["texto_creme"],
            relief="flat",
            bd=0,
            wrap="word",
            font=("Segoe UI", 10),
            padx=4,
            pady=4,
            cursor="arrow",
        )
        scroll_guia = ttk.Scrollbar(
            guia_box,
            orient="vertical",
            command=texto_guia.yview,
            style="Biblioteca.Vertical.TScrollbar",
        )
        texto_guia.configure(yscrollcommand=scroll_guia.set)
        texto_guia.pack(side="left", fill="both", expand=True)
        scroll_guia.pack(side="right", fill="y")

        texto_guia.tag_configure("titulo", font=("Segoe UI", 12, "bold"), foreground=PALETA["texto_creme"], spacing1=10, spacing3=4)
        texto_guia.tag_configure("sub", font=("Segoe UI", 10, "bold"), foreground=PALETA["texto_suave"], spacing1=4)
        texto_guia.tag_configure("corpo", font=("Segoe UI", 10), foreground=PALETA["texto_creme"], lmargin1=12, lmargin2=12, spacing3=3)

        blocos = [
            ("1. ATALHOS DE TECLADO", "titulo"),
            ("  • Ctrl + N : Abrir janela para cadastrar um Novo Livro na lista atual.\n"
             "  • Ctrl + E ou Duplo Clique na linha : Editar o livro selecionado.\n"
             "  • F (com um livro selecionado em Meus Livros) : Favoritar ou Desfavoritar (★ / ~).\n"
             "  • Delete (com um livro selecionado) : Deletar o livro (com confirmação).\n"
             "  • Ctrl + F : Focar diretamente na caixa de busca (Título/Autor).\n"
             "  • Ctrl + M (na Lista de Desejos) : Mover o livro selecionado para Meus Livros.\n"
             "  • Enter (dentro de janelas/diálogos) : Salvar e confirmar.\n"
             "  • Esc : Fechar janela aberta ou voltar para Meus Livros.", "corpo"),

            ("2. COMO ADICIONAR UM LIVRO EM CADA LISTA", "titulo"),
            ("  • Em Meus Livros (livros que você já possui):", "sub"),
            ("    1) Acesse '1- Meus Livros' no menu lateral.\n"
             "    2) Clique em '+ Novo Livro' (ou aperte Ctrl+N).\n"
             "    3) Preencha Título, marque se é Favorito (★), escolha ou digite uma Categoria, informe o Autor e o Valor (aceita vírgula ou ponto, ex.: 49,90) e clique em Salvar.", "corpo"),
            ("  • Em Lista de Desejos (livros que pretende comprar):", "sub"),
            ("    1) Acesse '2- Lista de Desejos' no menu lateral.\n"
             "    2) Clique em '+ Novo Livro' (ou aperte Ctrl+N).\n"
             "    3) Preencha Título, Categoria, Autor e Valor e clique em Salvar.", "corpo"),

            ("3. COMO FAVORITAR E DESFAVORITAR", "titulo"),
            ("  • Método rápido: selecione o livro na tabela de Meus Livros e clique no botão 'Favoritar / Desfavoritar' (ou aperte a tecla F).\n"
             "  • Pela edição: dê um duplo clique no livro (ou clique em 'Editar') e marque/desmarque 'Marcar como Favorito (★)'.\n"
             "  • Para ver apenas seus favoritos: marque a opção 'Somente Favoritos (★)' acima da tabela.", "corpo"),

            ("4. COMO FILTRAR, ORDENAR COLUNAS, CRIAR CATEGORIAS E MOVER DESEJOS", "titulo"),
            ("  • Ordenar colunas: clique no cabeçalho de qualquer coluna (#, Título, Fav, Categoria, Autor ou Valor) para alternar entre ordem crescente (▲) e decrescente (▼).\n"
             "  • Organizar colunas: arraste os cabeçalhos ou as divisórias entre colunas (inclusive a borda após Valor) para ajustar a largura.\n"
             "  • Criar Categoria: clique no botão 'Criar Categoria' no canto inferior direito para visualizar todas as categorias numeradas e cadastrar novas.\n"
             "  • Mover da Lista de Desejos para Meus Livros: selecione o livro desejado, clique em 'Mover para Meus Livros' (ou Ctrl+M) e escolha se deseja marcá-lo como Favorito.\n"
             "  • Recolher menu lateral: use o botão com o ícone de seta no canto superior esquerdo para encolher ou estender o menu.", "corpo"),

            ("5. MODO TERMINAL (CMD)", "titulo"),
            ("  • Abrir interface gráfica pelo CMD: python Interface.py  (ou  python Biblioteca.py --gui)\n"
             "  • Abrir modo clássico de texto no terminal: python Biblioteca.py", "corpo"),
        ]
        for texto, tag in blocos:
            texto_guia.insert("end", texto + "\n", tag)
        texto_guia.configure(state="disabled")

    def _criar_card_kpi(self, parent, col, titulo, valor_inicial, retornar_titulo=False, padx=(0, 0)):
        card = tk.Frame(
            parent,
            bg=PALETA["bg_card"],
            padx=16,
            pady=10,
            highlightthickness=1,
            highlightbackground=PALETA["acento"],
        )
        card.grid(row=0, column=col, sticky="ew", padx=padx)

        lbl_t = tk.Label(card, text=titulo, bg=PALETA["bg_card"], fg=PALETA["texto_suave"], font=FONTE_CARD_LABEL)
        lbl_t.pack(anchor="w")

        lbl_v = tk.Label(card, text=valor_inicial, bg=PALETA["bg_card"], fg=PALETA["texto_creme"], font=FONTE_CARD_VALOR)
        lbl_v.pack(anchor="w", pady=(2, 0))

        if retornar_titulo:
            return lbl_t, lbl_v
        return lbl_v

    def _configurar_atalhos(self):
        self.bind("<Control-n>", lambda _e: self._atalho_lista(self.adicionar_livro))
        self.bind("<Control-N>", lambda _e: self._atalho_lista(self.adicionar_livro))
        self.bind("<Control-e>", lambda _e: self._atalho_lista(self.editar_selecionado))
        self.bind("<Control-E>", lambda _e: self._atalho_lista(self.editar_selecionado))
        self.bind("<Control-f>", lambda _e: self._atalho_focar_busca())
        self.bind("<Control-F>", lambda _e: self._atalho_focar_busca())
        self.bind("<Control-m>", lambda _e: self.mover_selecionado() if self.tela_atual == "desejos" else None)
        self.bind("<Control-M>", lambda _e: self.mover_selecionado() if self.tela_atual == "desejos" else None)
        self.bind("<Delete>", lambda _e: self._atalho_fora_input(self.deletar_selecionado))
        self.bind("f", lambda _e: self._atalho_fora_input(self._atalho_favoritar))
        self.bind("F", lambda _e: self._atalho_fora_input(self._atalho_favoritar))
        self.bind("<Escape>", lambda _e: self._atalho_esc())

    def _atalho_lista(self, acao):
        if self.tela_atual in ("livros", "desejos"):
            acao()

    def _atalho_fora_input(self, acao):
        if self.tela_atual not in ("livros", "desejos"):
            return
        foco = self.focus_get()
        if isinstance(foco, (tk.Entry, ttk.Combobox)):
            return
        acao()

    def _atalho_favoritar(self):
        if self.tela_atual == "livros":
            self.alternar_favorito_selecionado()

    def _atalho_focar_busca(self):
        if self.tela_atual in ("livros", "desejos"):
            self.entry_busca.focus_set()

    def _atalho_esc(self):
        if self.tela_atual == "como_usar":
            self.ir_para("livros")

    def ir_para(self, tela):
        """Alterna entre Boas-Vindas, Meus Livros, Lista de Desejos e Como Usar."""
        self.tela_atual = tela
        self.ordem_coluna = None
        self.ordem_reversa = False
        self._suprimir_trace = False

        self.frame_boas_vindas.pack_forget()
        self.frame_lista.pack_forget()
        self.frame_como_usar.pack_forget()

        self._atualizar_sidebar()

        if tela == "boas_vindas":
            self.frame_boas_vindas.pack(fill="both", expand=True)
        elif tela == "como_usar":
            self.frame_como_usar.pack(fill="both", expand=True)
        else:
            self.linhas_brutas = []
            self.todos_validos = []
            self.itens_visiveis = []
            self._suprimir_trace = True
            try:
                self.var_busca.set("")
                self.var_categoria.set("Todas")
                self.var_so_favoritos.set(False)
            finally:
                self._suprimir_trace = False
            self._preparar_tela_lista()
            self.frame_lista.pack(fill="both", expand=True)
            self.recarregar_dados()

    def _atualizar_sidebar(self):
        mapa = {
            "livros": self.btn_nav_livros,
            "desejos": self.btn_nav_desejos,
            "como_usar": self.btn_nav_como_usar,
        }
        for chave, btn in mapa.items():
            ativo = chave == self.tela_atual
            bg = PALETA["acento"] if ativo else PALETA["bg_principal"]
            btn._bg_base = bg
            btn.configure(bg=bg)

    def _preparar_tela_lista(self):
        if self.tela_atual == "livros":
            self.lbl_secao_titulo.configure(text="Meus Livros")
            self.lbl_secao_subtitulo.configure(text="Gerencie sua coleção de livros adquiridos")
            self.chk_fav.pack(side="left", padx=(0, 8))
            self.btn_favoritar.pack(side="left", padx=(0, 8))
            self.btn_mover.pack_forget()
            self.lbl_kpi_extra_titulo.configure(text="FAVORITOS")
        else:
            self.lbl_secao_titulo.configure(text="Lista de Desejos")
            self.lbl_secao_subtitulo.configure(text="Acompanhe os livros que você pretende adquirir")
            self.chk_fav.pack_forget()
            self.btn_favoritar.pack_forget()
            self.btn_mover.pack(side="left", padx=(0, 8))
            self.lbl_kpi_extra_titulo.configure(text="CATEGORIAS")

        self._configurar_colunas_tabela()

    def _configurar_colunas_tabela(self):
        if self.tela_atual == "livros":
            colunas = ("num", "titulo", "fav", "categoria", "autor", "valor", "espaco")
            self.tree.configure(columns=colunas)
            self._configs_colunas = [
                ("num", "#", 48, "center", False),
                ("titulo", "Título do Livro", 260, "w", True),
                ("fav", "Fav", 65, "center", False),
                ("categoria", "Categoria", 150, "center", False),
                ("autor", "Autor", 190, "center", True),
                ("valor", "Valor", 130, "center", False),
                ("espaco", "", 30, "center", True),
            ]
        else:
            colunas = ("num", "titulo", "categoria", "autor", "valor", "espaco")
            self.tree.configure(columns=colunas)
            self._configs_colunas = [
                ("num", "#", 48, "center", False),
                ("titulo", "Título do Livro", 290, "w", True),
                ("categoria", "Categoria", 170, "center", False),
                ("autor", "Autor", 210, "center", True),
                ("valor", "Valor", 130, "center", False),
                ("espaco", "", 30, "center", True),
            ]

        self._atualizar_cabecalhos_ordenacao()

    def _atualizar_cabecalhos_ordenacao(self):
        for col_id, texto, largura, ancora, esticar in self._configs_colunas:
            if col_id == "espaco":
                self.tree.heading(col_id, text="")
                self.tree.column(col_id, width=largura, minwidth=15, anchor=ancora, stretch=esticar)
                continue

            seta = ""
            if self.ordem_coluna == col_id:
                seta = " ▼" if self.ordem_reversa else " ▲"
            self.tree.heading(
                col_id,
                text=f"{texto}{seta}",
                command=lambda c=col_id: self._ordenar_por_coluna(c),
            )
            self.tree.column(col_id, width=largura, minwidth=45, anchor=ancora, stretch=esticar)

    def _ordenar_por_coluna(self, coluna):
        if self.ordem_coluna == coluna:
            self.ordem_reversa = not self.ordem_reversa
        else:
            self.ordem_coluna = coluna
            self.ordem_reversa = False
        self._atualizar_cabecalhos_ordenacao()
        self.aplicar_filtros()

    def _caminho_ativo(self):
        return Biblioteca.arquivoLivros if self.tela_atual == "livros" else Biblioteca.arquivoListaDesejo

    def _com_favorito_ativo(self):
        return self.tela_atual == "livros"

    def _limpar_filtros(self):
        self.var_busca.set("")
        self.var_categoria.set("Todas")
        self.var_so_favoritos.set(False)
        self.aplicar_filtros()

    def recarregar_dados(self):
        if self.tela_atual not in ("livros", "desejos"):
            return
        categorias = ["Todas", *Biblioteca._ler_categorias()]
        self.combo_filtro_cat.configure(values=categorias)
        if self.var_categoria.get() not in categorias:
            self.var_categoria.set("Todas")

        self.linhas_brutas, self.todos_validos, self.qtd_invalidas = Biblioteca._carregar_linhas_arquivo(
            self._caminho_ativo(), com_favorito=self._com_favorito_ativo()
        )
        self.aplicar_filtros()

    def aplicar_filtros(self):
        if self.tela_atual not in ("livros", "desejos"):
            return
        com_fav = self._com_favorito_ativo()
        filtrados = _filtrar_registros(
            self.todos_validos,
            com_favorito=com_fav,
            termo=self.var_busca.get(),
            categoria=self.var_categoria.get(),
            apenas_favoritos=self.var_so_favoritos.get() if com_fav else False,
        )
        if self.ordem_coluna:
            self.itens_visiveis = _ordenar_itens(filtrados, self.ordem_coluna, self.ordem_reversa, com_fav)
        else:
            self.itens_visiveis = filtrados

        for item in self.tree.get_children():
            self.tree.delete(item)

        soma = 0.0
        favoritos = 0
        categorias_unicas = set()

        for pos, (_idx_bruto, campos, valor) in enumerate(self.itens_visiveis, start=1):
            tag = "par" if pos % 2 == 1 else "impar"
            if com_fav:
                nome, fav, cat, autor = campos
                if fav == "★":
                    favoritos += 1
                valores = (pos, nome, fav, cat, autor, f"R$ {valor:,.2f}", "")
            else:
                nome, cat, autor = campos
                categorias_unicas.add(cat)
                valores = (pos, nome, cat, autor, f"R$ {valor:,.2f}", "")

            self.tree.insert("", "end", iid=str(pos - 1), values=valores, tags=(tag,))
            soma += valor

        self.lbl_kpi_qtd.configure(text=str(len(self.itens_visiveis)))
        self.lbl_kpi_valor.configure(text=f"R$ {soma:,.2f}")
        self.lbl_kpi_extra_valor.configure(text=str(favoritos if com_fav else len(categorias_unicas)))

        if self.qtd_invalidas > 0:
            self.lbl_aviso.configure(
                text=f"Aviso: {self.qtd_invalidas} linha(s) malformada(s) no CSV ignorada(s) na exibição e preservada(s) ao salvar."
            )
        else:
            self.lbl_aviso.configure(
                text="Dica: clique nos cabeçalhos para ordenar | duplo clique para editar | tecla F para favoritar/desfavoritar."
            )

    def _indice_selecionado(self):
        selecao = self.tree.selection()
        if not selecao:
            messagebox.showinfo("Seleção", "Selecione um livro na tabela primeiro.", parent=self)
            return None
        return int(selecao[0])

    def adicionar_livro(self):
        dialogo = DialogoLivro(self, com_favorito=self._com_favorito_ativo())
        self.wait_window(dialogo)
        if dialogo.resultado is None:
            return
        campos, valor, capa = dialogo.resultado
        Biblioteca._adicionar_registro(self._caminho_ativo(), campos, valor, capa=capa)
        self.recarregar_dados()

    def editar_selecionado(self):
        pos = self._indice_selecionado()
        if pos is None:
            return
        idx_bruto, campos, valor = self.itens_visiveis[pos]
        com_fav = self._com_favorito_ativo()
        dados_iniciais = (*campos, valor)
        capa_atual = Biblioteca._extrair_capa_linha(self.linhas_brutas[idx_bruto], com_favorito=com_fav)

        dialogo = DialogoLivro(
            self,
            com_favorito=com_fav,
            dados_iniciais=dados_iniciais,
            capa_inicial=capa_atual,
        )
        self.wait_window(dialogo)
        if dialogo.resultado is None:
            return

        novos_campos, novo_valor, nova_capa = dialogo.resultado
        self.linhas_brutas[idx_bruto] = Biblioteca._formatar_linha_csv(
            novos_campos, novo_valor, capa=nova_capa
        )
        Biblioteca._salvar_linhas_brutas(self._caminho_ativo(), self.linhas_brutas)
        self.recarregar_dados()

    def alternar_favorito_selecionado(self):
        if self.tela_atual != "livros":
            return
        pos = self._indice_selecionado()
        if pos is None:
            return
        idx_bruto, campos, valor = self.itens_visiveis[pos]
        nome, fav_atual, categoria, autor = campos
        novo_fav = "~" if fav_atual == "★" else "★"
        capa_atual = Biblioteca._extrair_capa_linha(self.linhas_brutas[idx_bruto], com_favorito=True)
        self.linhas_brutas[idx_bruto] = Biblioteca._formatar_linha_csv(
            [nome, novo_fav, categoria, autor], valor, capa=capa_atual
        )
        Biblioteca._salvar_linhas_brutas(Biblioteca.arquivoLivros, self.linhas_brutas)
        self.recarregar_dados()

    def deletar_selecionado(self):
        pos = self._indice_selecionado()
        if pos is None:
            return
        idx_bruto, campos, _valor = self.itens_visiveis[pos]
        confirmar = messagebox.askyesno(
            "Confirmar exclusão",
            f'Tem certeza que deseja deletar "{campos[0]}"?',
            parent=self,
        )
        if not confirmar:
            return

        del self.linhas_brutas[idx_bruto]
        Biblioteca._salvar_linhas_brutas(self._caminho_ativo(), self.linhas_brutas)
        self.recarregar_dados()

    def mover_selecionado(self):
        if self.tela_atual != "desejos":
            return
        pos = self._indice_selecionado()
        if pos is None:
            return
        idx_bruto, campos, valor = self.itens_visiveis[pos]
        nome, categoria, autor = campos

        resposta = messagebox.askyesnocancel(
            "Mover para Meus Livros",
            f'Deseja marcar "{nome}" como Favorito (★)?',
            parent=self,
        )
        if resposta is None:
            return

        favorito = "★" if resposta else "~"
        capa_atual = Biblioteca._extrair_capa_linha(self.linhas_brutas[idx_bruto], com_favorito=False)
        Biblioteca._adicionar_registro(
            Biblioteca.arquivoLivros,
            [nome, favorito, categoria, autor],
            valor,
            capa=capa_atual,
        )
        del self.linhas_brutas[idx_bruto]
        Biblioteca._salvar_linhas_brutas(Biblioteca.arquivoListaDesejo, self.linhas_brutas)
        self.recarregar_dados()
        messagebox.showinfo("Sucesso", f'"{nome}" movido para Meus Livros!', parent=self)

    def gerenciar_categorias(self):
        dialogo = DialogoCategorias(self)
        self.wait_window(dialogo)
        self.recarregar_dados()


def iniciar_interface():
    """Inicia a janela gráfica da Biblioteca de Livros."""
    app = BibliotecaApp()
    app.mainloop()


if __name__ == "__main__":
    iniciar_interface()
