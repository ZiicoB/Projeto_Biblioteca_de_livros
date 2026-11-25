# Projeto Facultativo (Avaliativo): Biblioteca de Livros (Python)
Projeto avaliativo para a cadeira — Fundamentos da Programação.    
Projeto realizado por:    
+ **Adriano Barnard Medeiros** 

> O programa foi criado para gerenciar uma biblioteca pessoal de livros em linha de comando (CLI),
> onde o usuário pode cadastrar os livros que já possui e os livros que deseja comprar,
> organizados por **(Nome, Favorito, Categoria, Autor e Valor)**.
>> É possível adicionar novas categorias ao cadastrar ou editar um livro.    
>> Também é possível alterar parcialmente (mantendo campos com Enter), deletar com confirmação
>> e mover livros da Lista de Desejos para Meus Livros.
>
> ![Tabela_De_Livros](./Arquivos/Imagens/Tabela.png)
>
> O usuário pode filtrar e verificar seus livros por:    
> + **Categoria**
> + **Autor** (busca parcial)
> + **Livros Favoritos**
>
>![Menu_Principal](./Arquivos/Imagens/Menu.png)
>
## Manual e Fluxograma 
[<img src="./Arquivos/Imagens/pdf_icone.png" width="80">](./Arquivos/Manual/Manual_da_Biblioteca.pdf)
[<img src="./Arquivos/Imagens/Fluxograma.png" width="80">](./Arquivos/Manual/Fluxograma.pdf)

## Atualizações (25/11/2026)
*Correções feitas com uso de IA.*

- Correção de validações e tratamento de erros nos menus e cadastros.
- Leitura e gravação segura em CSV (suporte a vírgulas e preservação de dados).
- Adição de edição parcial, confirmação ao deletar e opção de mover livros da Lista de Desejos para Meus Livros.
- Interface gráfica em `tkinter` (`python Interface.py` ou `python Biblioteca.py --gui`).
- Limpeza do código e inclusão de testes unitários básicos.
