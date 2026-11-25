# Biblioteca de Livros (Python)

Projeto avaliativo para a disciplina **Fundamentos da Programação**.  
Desenvolvido por **Adriano Barnard Medeiros**.

O programa gerencia uma biblioteca pessoal de livros, permitindo controlar os livros que você já possui (**Meus Livros**) e os que pretende comprar (**Lista de Desejos**), organizados por **Título, Favorito, Categoria, Autor, Valor** e **Capa (opcional)**, com persistência em arquivos CSV na pasta `Arquivos/`.

---

## Como Abrir o Programa

### 1. Interface Gráfica (Recomendado)
Abra o **CMD** (ou terminal) na pasta do projeto e execute:

```cmd
python Interface.py
```

Também é possível iniciar a interface diretamente pelo arquivo principal com:

```cmd
python Biblioteca.py --gui
```

### 2. Modo Terminal (Clássico)
Para usar a versão original em texto no terminal:

```cmd
python Biblioteca.py
```

---

## Como Usar pela Interface Gráfica

- **Menu Lateral Retrátil**: alterne entre **1- Meus Livros**, **2- Lista de Desejos** e **3- Como Usar**. Use o botão com seta no canto superior esquerdo para recolher ou estender a barra lateral.
- **Cadastrar Livro (`+ Novo Livro` ou `Ctrl+N`)**:
  - Preencha **Título**, marque se é **Favorito (★)** (em Meus Livros), escolha ou digite uma **Categoria**, informe o **Autor** e o **Valor** (aceita vírgula ou ponto, ex.: `49,90`).
  - No painel direito (**Capa do Livro**), clique em **Escolher Imagem** para anexar uma capa opcional (`PNG`, `JPG`, `GIF` ou `BMP`).
- **Editar e Favoritar (`Editar`, duplo clique ou `Ctrl+E`)**:
  - Dê um duplo clique em qualquer livro para editar seus dados ou trocar/remover a capa.
  - Para favoritar ou desfavoritar rapidamente em *Meus Livros*, selecione o item e clique em **Favoritar / Desfavoritar** (ou pressione **`F`**).
- **Filtrar e Ordenar**:
  - Use a barra de busca por **Título/Autor**, o seletor de **Categoria** e o filtro **Somente Favoritos (★)**.
  - Clique no cabeçalho de qualquer coluna (`#`, `Título`, `Fav`, `Categoria`, `Autor` ou `Valor`) para ordenar em ordem crescente (`▲`) ou decrescente (`▼`).
- **Mover Desejos e Deletar**:
  - Em *Lista de Desejos*, selecione um livro e clique em **Mover para Meus Livros** (`Ctrl+M`) para transferi-lo após a compra.
  - Clique em **Deletar** (`Delete`) para excluir um registro (com confirmação).
- **Criar e Gerenciar Categorias (`Criar Categoria`)**:
  - No canto inferior direito, abra a janela paginada (`20`, `30`, `40` ou `60` por página) para adicionar, editar ou excluir categorias.

### Atalhos Rápidos
| Atalho | Ação |
| --- | --- |
| `Ctrl + N` | Novo livro na lista atual |
| `Ctrl + E` / Duplo clique | Editar livro selecionado |
| `F` | Favoritar / Desfavoritar (em Meus Livros) |
| `Delete` | Deletar livro selecionado |
| `Ctrl + F` | Focar na busca por Título/Autor |
| `Ctrl + M` | Mover livro da Lista de Desejos para Meus Livros |
| `Esc` | Fechar janela ou sair da tela Como Usar |

---

## Imagens da Interface

<!-- Substitua os caminhos abaixo pelas novas capturas colocadas em ./Arquivos/Imagens/ -->
> *Espaço reservado para as novas capturas de tela da interface gráfica:*

| Tela Principal (Meus Livros) | Cadastro / Edição com Capa |
| :---: | :---: |
| ![Interface Meus Livros](./Arquivos/Imagens/Tabela.png) | ![Cadastro com Capa](./Arquivos/Imagens/Menu.png) |

| Gerenciar Categorias | Tela Como Usar |
| :---: | :---: |
| *Adicione aqui sua captura de Categorias* | *Adicione aqui sua captura de Como Usar* |

---

## Manual e Fluxograma

[<img src="./Arquivos/Imagens/pdf_icone.png" width="80">](./Arquivos/Manual/Manual_da_Biblioteca.pdf)
[<img src="./Arquivos/Imagens/Fluxograma.png" width="80">](./Arquivos/Manual/Fluxograma.pdf)

---

## Atualizações (25/11/2026)
*Correções feitas com uso de IA.*

- Correção de validações e tratamento de erros nos menus e cadastros.
- Leitura e gravação segura em CSV (suporte a vírgulas e preservação de dados).
- Adição de edição parcial, confirmação ao deletar e opção de mover livros da Lista de Desejos para Meus Livros.
- Interface gráfica em `tkinter` (`python Interface.py` ou `python Biblioteca.py --gui`) com suporte a capa do livro e paginação de categorias.
- Foi criado uma janela de como usar o programa.
- Limpeza do código e inclusão de testes unitários básicos (`python -m unittest discover -s tests`).
