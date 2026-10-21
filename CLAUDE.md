# Painel do Bar — instruções para o Claude Code

App desktop (Windows) em Python + CustomTkinter para o dono de um bar abrir
rápido as planilhas e outros arquivos de controle e fazer backup na nuvem
(com botão ou toda semana, sozinho). Quem usa e mantém é o Filipe, que está
começando na área de tecnologia: explique as mudanças em português simples e
mantenha os comentários e textos da interface em português.

O LEIA-ME.md é o manual do usuário. Este arquivo é o guia para mexer no código.

## Comandos (Windows, na pasta do projeto)

```
gerar_exe.bat                                   cria .venv, instala tudo e gera dist\PainelDoBar.exe
publicar_versao.bat                             versão nova: testes + .exe + git push + release no GitHub
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest                  testes do núcleo (precisam passar sempre)
.venv\Scripts\python main.py                    abre o painel direto do código
.venv\Scripts\python main.py --backup           faz o backup sem janela (o que o agendamento roda)
.venv\Scripts\python ferramentas\capturar_telas.py   salva uma imagem de cada tela em capturas\
```

`capturar_telas.py` aceita `--tema claro|escuro|ambos` e `--cenas principal editar ...`.
Use-o para **ver** o resultado de qualquer mudança visual: rode e abra os PNGs.
Ele usa dados de exemplo numa pasta temporária (`ferramentas/dados_exemplo.py`).

**Dados reais:** o Filipe usa o .exe em `C:\PainelDoBar\`, com os dados em
`C:\PainelDoBar\Dados\`. Nunca rode testes, capturas ou o app apontando para lá.
Rodando pelo código, o app usa `Dados\` dentro do projeto (está no .gitignore),
e a variável `PAINEL_DADOS` troca a pasta.

Depois de gerar um .exe novo, basta substituir o `C:\PainelDoBar\PainelDoBar.exe`:
a pasta `Dados` continua igual.

## Arquitetura

```
main.py            entrada: abre a janela, ou faz backup silencioso com --backup
app/core/          REGRAS, sem nenhum import de interface (testável)
  panel.py         fachada: a interface e o modo silencioso só falam com Panel
  library.py       cartões: sincroniza com a pasta, adiciona (mover/copiar/atalho), remove, edita, ordena
  backup.py        zip com data -> confere -> copia para a pasta da nuvem -> apaga antigos (retenção)
  scheduler.py     tarefa semanal no Agendador do Windows (schtasks + XML em UTF-16)
  models.py        Item, Settings, BackupRecord (from_dict ignora campos desconhecidos)
  storage.py       config.json com versão de esquema e espaço para migrações
  file_types.py    extensão -> categoria (rótulo e cor da capa)
  excel.py         backup pelo botão: salva e fecha no Excel aberto as planilhas do painel (PowerShell + COM)
  updater.py       atualização: último release do GitHub -> baixa .new.exe -> PowerShell troca e reabre
app/ui/            TELA (CustomTkinter)
  theme.py         TODOS os tokens visuais: cores (pares claro/escuro), fontes, medidas, botões prontos
  art.py           Pillow: capas sem foto (cor lisa + bolhas de sabão), selos, cantos arredondados, logo
  main_window.py   monta a tela e liga botões às ações do Panel
  widgets/         header, filters, card_grid (place + animação ao arrastar), card, backup_bar, toast,
                   update_bar, popup_menu (menu dos três pontinhos e do Adicionar)
  dropfiles.py     soltar arquivos do Explorer na janela (WM_DROPFILES via ctypes; copia para Arquivos)
  dialogs/         base (Dialog + message/confirm), edit_item, add_items, settings
  notification.py  aviso no canto da tela do backup automático
app/silent.py      backup sem janela
ferramentas/       dados de exemplo e captura de telas (desenvolvimento)
testes/            pytest do núcleo
```

Regras de arquitetura:
- `app/core` nunca importa nada de `app/ui`.
- Regras novas vão para o núcleo, com teste. A tela só chama o `Panel`.
- Cores, fontes e medidas ficam só em `theme.py`. Não espalhe hex pelo código.
- Erros mostrados ao usuário vêm de exceções do núcleo (LibraryError, SchedulerError,
  ImageError...) que já trazem a mensagem pronta em português.

## Comportamentos que não podem quebrar

- Nome, foto, descrição e cor do cartão existem **só no painel**. O arquivo real nunca é renomeado.
- Arquivo colocado/tirado da pasta `Dados\Arquivos` aparece/some sozinho (a janela confere a cada 2 s).
- Arquivo solto do Explorer na janela é **copiado** para `Dados\Arquivos` (o original fica onde estava).
- Remover pelo painel **nunca apaga**: move para `Dados\Removidos`.
- O backup inclui a pasta Arquivos, os atalhos (vinculados) e `Sistema/` (config e fotos).
  Se a nuvem estiver fora do ar, o backup fica no PC com aviso, sem falhar.
- Planilha aberta no Excel é detectada pelo arquivo de trava `~$nome` (selo "Aberto agora").
- **Só no backup pelo botão**, o painel salva e fecha no Excel as planilhas dele (pasta Arquivos
  e atalhos) antes de copiar. Nunca toca em planilha de fora nem em "somente leitura", e só fecha
  o Excel se não sobrar outra planilha aberta. O backup automático não mexe no Excel.

## Git, GitHub e atualizações

- Repositório **público**: github.com/FilipeNsdev/painel-do-bar (`UPDATE_REPO` em `app/__init__.py`).
  Nada de dados do bar no Git: `Dados/` está no `.gitignore`.
- Ramo `main`. Commit e push só quando o Filipe pedir; publicar versão é com `publicar_versao.bat`
  (`ferramentas/publicar_versao.py`), que cria a etiqueta `vX.Y.Z` e o release com o `PainelDoBar.exe`.
- O painel (.exe) pergunta `releases/latest` ao abrir, em segundo plano, sem token. Sem internet: nada acontece.
- A troca do .exe espera o processo do painel **e o pai** (o .exe de arquivo único do PyInstaller
  tem dois processos) fecharem; o antigo vira `PainelDoBar.old.exe` e é apagado na abertura seguinte.

## Identidade visual atual (pode mudar, mas com motivo)

A do Bar do Sabão, igual à do Conciliador Stone (o outro app do bar): branco
limpo, texto quase preto e uma cor só, o vermelho da camisa do Sabão
(`#C8102E`), nos botões principais e na faixa de 3 px no topo do cabeçalho.
A logo real (o Sabão de camisa vermelha, recortada em círculo) está em
`assets/logo.png`; o ícone do .exe sai dela com `empacotamento/gerar_icone.py`.

- Uma família de letra só: Segoe UI (o nome do painel em negrito 26).
  A fonte Alfa Slab One em `assets/fontes` não é mais usada.
- Superfícies separadas por degrau de tom, sem linhas nem sombras. Linha só em campo de texto.
- Botões, campos e filtros sempre em formato de pílula (`RADIUS_CONTROL` = metade da altura).
- Vermelho só onde há ação ou "solte aqui". Escolhido (filtro, aba) = pílula preta.
- Capas sem foto: cor lisa, bolhas de sabão claras subindo do canto direito
  e a extensão em Segoe UI Black embaixo à esquerda.
- No Windows 11 a barra de título das janelas é pintada com a cor do cabeçalho
  (`style_titlebar` em `dialogs/base.py`), senão aparece a cor de destaque do Windows.
- Textos da interface em frases curtas, voz ativa, sem caixa alta e sem setas.

## Armadilhas já encontradas (CustomTkinter / Tk / PyInstaller)

- `CTkEntry`: o `placeholder_text` **não aparece** se usar `textvariable`. Leia com `.get()`.
- Não crie atributos com nomes que já existem no tkinter (`_options`, `title`, `location`...):
  o erro aparece longe dali ("'list' object is not callable").
- `CTkLabel` tem altura padrão 28: para linhas de texto juntas, passe `height` menor.
- `CTkFrame` tem tamanho padrão 200x200: barrinhas com `fill="y"` precisam de `height=1`.
- `CTkToplevel` troca o ícone 200 ms depois de criada: por isso `set_window_icon` roda com `after(260)`.
- A barra de rolagem do `CTkScrollableFrame` aparece mesmo sem conteúdo para rolar:
  `CardGrid._sync_scrollbar` esconde a barra quando tudo cabe.
- Fotos e capas já saem com os cantos arredondados na cor de fundo (claro e escuro) via
  `art.card_image`. Se mudar `surface` no tema, elas acompanham.
- PyInstaller: sem `PIL._tkinter_finder` nos hiddenimports o .exe **fecha ao abrir**. Está no `.spec`.
- `.bat` precisa de quebra de linha CRLF e só caracteres ASCII.
- `gerar_exe.bat` falhando com "Acesso negado" em `build\PainelDoBar\localpycs`: a pasta ficou
  "somente leitura". Rode `attrib -R build\* /S /D` e apague a pasta `build` (é só sobra do build).
- Python 3.14.7+ no Windows usa Tk 9. Foi testado e funciona (inclusive o .exe).
- `wraplength` do CTkLabel é multiplicado pelo zoom do Windows; o `event.width` do `<Configure>`
  já vem em pixels reais. Divida pelo `ScalingTracker.get_widget_scaling` antes de usar.
- `CardGrid` posiciona os cartões com `place` para animar. Com `place`, o miolo do
  `CTkScrollableFrame` não ganha altura sozinho: use `tkinter.Frame.configure(self, height=...)`
  em pixels reais. O `configure(height=...)` do CTk muda a área **visível**, e os cartões somem.
- Trocar claro/escuro: o CustomTkinter esconde e mostra cada janela para repintar a barra de
  título. Com um diálogo aberto (grab), ele "fecha" e o painel trava. Por isso `apply_theme`
  liga `_deactivate_windows_window_header_manipulation` e quem pinta a barra é `style_titlebar`.
- `PopupMenu` não pode fechar só porque perdeu o foco: o painel pega o foco de volta logo
  depois de abrir. Ele fecha com clique fora, Esc ou quando o foco sai do programa.
- Ajudante da atualização (PowerShell aberto pelo .exe): precisa de console escondido
  (`CREATE_NO_WINDOW`; com `DETACHED_PROCESS` ele morre calado), sair do "job" do .exe
  (`CREATE_BREAKAWAY_FROM_JOB`, senão morre junto) e abrir o painel novo sem as variáveis
  `_PYI_*` herdadas (`PYINSTALLER_RESET_ENVIRONMENT=1`). Ele anota tudo em `%TEMP%\PainelDoBar_atualizacao.log`.
- No Windows, uma janela nova não vem para a frente sozinha: `capturar_telas.py` põe tudo
  em `-topmost` só na hora da foto. Sem isso as imagens saem com o que estiver por cima.

## Testado no Windows 11 (outubro de 2026, zoom 125%)

- `scheduler.py`: tarefa criada, rodou o `--backup` sozinha e fez o zip, removida. Tem
  `StartWhenAvailable` (roda quando o PC ligar se estava desligado), mas isso não foi visto acontecer.
- `shortcuts.py`: atalho criado na Área de Trabalho com o alvo certo.
- `single_instance.py`: a segunda cópia fecha e a janela aberta volta (inclusive minimizada).
- `notification.py`: aviso no canto certo, acima da barra de tarefas, com 125%. Falta ver 150%.
- Abrir pasta (`os.startfile`) e "Mostrar na pasta" (arquivo com acento selecionado).
- Selo "Aberto agora" com o Excel 16 real: aparece com a planilha aberta e some ao fechar.

- `excel.py`: o Excel só aparece para o `GetActiveObject` se foi aberto pelo usuário (ou com
  `Visible` + `UserControl`). Depois do `Quit` o processo `EXCEL.EXE` pode ficar vivo sem janela
  por um tempo; é inofensivo (a próxima planilha abre nele normalmente). Não mate o processo.
- Backup pelo botão com o Excel 16 real: salvou e fechou só a planilha do painel, deixou aberta
  a de fora com a mudança, fechou o Excel quando não sobrou nada e o zip levou a versão nova.
  Não testado: célula em edição (deve cair na mensagem "Aperte Enter ou Esc").

## Pontos de design já notados

- Menus de contexto (`tkinter.Menu`) são nativos e não seguem o tema.
- Diálogos repetem o título da janela no cabeçalho interno.
- Cartões não têm navegação por teclado nem foco visível.
- Conferir com zoom de 150% e em telas pequenas (1366x768).
