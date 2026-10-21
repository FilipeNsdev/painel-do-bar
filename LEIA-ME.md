# Painel do Bar

Um painel para abrir rapidinho as planilhas e os outros arquivos do bar e
fazer backup deles na nuvem, com um botão ou sozinho toda semana.

- Cada arquivo vira um **cartão** com foto (ou capa colorida), nome e descrição.
- Aceita **qualquer arquivo**: planilhas (inclusive .xlsm com macros), PDFs,
  documentos, fotos, pastas inteiras e até **sites** (portal da NF-e, banco...).
- **Nome, foto e descrição mudam só no painel.** O arquivo de verdade nunca é
  renomeado.
- **Backup** em .zip com data, copiado para o Google Drive (ou OneDrive) e
  guardado também no computador.

---

## 1. Gerar o executável (uma vez só)

1. Instale o **Python 3.13 ou 3.14** pelo site <https://www.python.org/downloads/windows/>.
   Na primeira tela da instalação, marque **"Add python.exe to PATH"**.
2. Dê dois cliques em **`gerar_exe.bat`**. Na primeira vez demora alguns
   minutos. No fim, abre a pasta `dist` com o **`PainelDoBar.exe`**.
   O script mostra qual Python usou. Se tiver mais de um instalado, ele
   prefere o 3.13.

> **Se as janelas aparecerem estranhas** (cantos quadrados ou serrilhados,
> letra diferente) com o Python 3.14: instale também o Python 3.13
> ("Windows installer 64-bit"), apague a pasta `.venv` do projeto e rode o
> `gerar_exe.bat` de novo. O 3.14 usa uma versão nova do Tk, que desenha as
> janelas, e o 3.13 é o mais testado com o CustomTkinter.
3. Crie a pasta **`C:\PainelDoBar`** e copie o `PainelDoBar.exe` para dentro dela.
4. Abra o programa. Em **Configurações > Painel**, clique em
   **"Criar atalho na Área de Trabalho"**.

> O Python só é necessário para **gerar** o .exe. Depois disso o
> `PainelDoBar.exe` funciona sozinho, inclusive em outro computador.

**Se o Windows ou o antivírus reclamar:** programas novos, sem assinatura
digital, às vezes são bloqueados. No aviso azul do Windows, clique em
"Mais informações" e depois em "Executar assim mesmo". Se o antivírus
colocar em quarentena, libere o arquivo uma vez.

## 2. Primeira vez

Ao abrir, o painel cria a pasta **`Dados`** ao lado do executável:

```
C:\PainelDoBar\
    PainelDoBar.exe
    Dados\
        Arquivos\    <- os arquivos do painel ficam aqui
        Backups\     <- cópias dos backups neste computador
        Removidos\   <- o que você tirou do painel (nada é apagado)
        Sistema\     <- configurações, fotos dos cartões e registros (não mexer)
```

Depois, configure a nuvem:

1. Instale o **Google Drive para computador** e entre na sua conta. Ele
   cria uma unidade (normalmente `G:`) com a pasta "Meu Drive".
2. No painel, abra **Configurações > Backup** e clique em
   **"Usar Google Drive (G:)"**. O painel sugere a pasta
   `G:\Meu Drive\Backups Painel do Bar`.
3. Ligue **"Fazer backup toda semana"** e escolha o dia e a hora.
4. Clique em **Salvar** e depois em **Fazer backup agora** para testar.

## 3. Usando no dia a dia

| Quero... | Como |
|---|---|
| Abrir um arquivo | Clique no cartão. |
| Trocar nome, foto, descrição ou cor | Botão `···` do cartão (ou clique direito) > **Editar nome, foto e cor**. |
| Mudar a ordem | Arraste um cartão para cima de outro. |
| Achar um arquivo | Digite na busca (não precisa de acento) ou use os filtros por tipo. |
| Adicionar | Botão **Adicionar** > Arquivos, Uma pasta inteira ou Um site. |
| Remover | `···` > **Remover do painel**. |

### Adicionar e remover: pelo painel ou pela pasta, tanto faz

**Jeito mais rápido:** arraste arquivos do Windows Explorer (ou da Área de
Trabalho) e solte em cima do painel. Eles são **copiados** para a pasta do
painel e viram cartões na hora. O original continua onde estava.

Para mudar a ordem dos cartões, arraste um cartão: os outros abrem espaço
enquanto você arrasta. Os três pontinhos de cada cartão abrem o menu com
abrir, mostrar na pasta, editar, mover e remover.

As duas formas funcionam ao mesmo tempo:

- **Pela pasta:** coloque um arquivo em `Dados\Arquivos` e em até 2 segundos
  ele aparece no painel. Tire de lá e ele some.
- **Pelo painel:** ao adicionar um arquivo que está em outro lugar, o painel
  pergunta o que fazer:
  - **Mover para o painel:** o arquivo passa a morar na pasta do painel.
  - **Copiar para o painel:** o painel guarda uma cópia; o original fica onde estava.
  - **Deixar onde está:** vira um **atalho**. O arquivo continua no lugar
    e entra no backup do mesmo jeito.

**Remover** nunca apaga nada: o arquivo vai para `Dados\Removidos`, com a
data no começo do nome. Para trazer de volta, mova-o de novo para
`Dados\Arquivos` (ele volta como um cartão novo).

Se um arquivo sair da pasta por fora do painel (pelo Explorer, por exemplo)
e voltar com o mesmo nome em até 30 dias, o cartão volta com o nome e a
foto que você tinha escolhido.

O selo **"Aberto agora"** aparece quando a planilha está aberta no Excel.

## 4. Backup

**O que entra:** tudo da pasta `Dados\Arquivos` (com subpastas), os arquivos
dos atalhos e as configurações do painel (nomes, fotos e ordem dos cartões).
Dá para deixar um cartão de fora em **Editar > Incluir no backup**.

**Para onde vai:** um arquivo `Backup_PainelDoBar_2026-10-21_22h00.zip` em
`Dados\Backups` **e** na pasta da nuvem. Os mais antigos são apagados
sozinhos (padrão: guarda os últimos 10).

**Quando:**

- quando você clica em **Fazer backup agora**;
- toda semana, no dia e hora escolhidos. Se o computador estiver desligado
  nesse horário, roda quando ele ligar;
- ao abrir o painel, se o último backup tiver mais de 7 dias.

**Se a nuvem estiver desconectada,** o backup fica no computador e o
rodapé do painel avisa.

**Para recuperar um arquivo:** abra o .zip (dois cliques), entre em
`Arquivos` e arraste o arquivo para fora. Dentro do .zip, o `LEIA-ME.txt`
lista o que tem nele.

**Planilhas abertas no Excel:** ao clicar em **Fazer backup agora**, o painel
salva as planilhas dele que estiverem abertas, fecha essas planilhas e só
depois faz o backup. Assim a versão que sobe para a nuvem é a mais nova.

- Planilhas de fora do painel não são tocadas: ficam abertas como estavam.
- O Excel só fecha de vez se não sobrar nenhuma outra planilha aberta nele.
- Planilha aberta como "somente leitura" não pode ser salva, então fica aberta.
- Se você estiver digitando dentro de uma célula, o Excel não responde: o
  painel avisa para apertar Enter (ou Esc) e clicar de novo.

Isso acontece **só pelo botão**. No backup automático da semana (e no que roda
ao abrir o painel), o painel não mexe no Excel: planilha aberta entra com a
última versão salva.

## 5. Como o código está organizado

As regras ficam no `app/core` e a tela fica no `app/ui`. A tela só conversa
com a classe `Panel`. Assim dá para mudar o visual sem mexer nas regras, e o
backup automático usa as mesmas regras sem abrir janela.

```
main.py                     ponto de entrada (abre o painel ou faz backup com --backup)
app/
  core/                     REGRAS (sem nada de tela)
    panel.py                junta tudo: é com ele que a tela conversa
    library.py              cartões: sincronizar com a pasta, adicionar, remover, editar, ordenar
    backup.py               monta o .zip, confere, copia para a nuvem, apaga os antigos
    scheduler.py            backup semanal no Agendador de Tarefas do Windows
    models.py               formato dos dados (Item, Settings, BackupRecord)
    storage.py, jsonfile.py gravação segura da configuração (com cópia .bak)
    history.py              histórico dos backups
    file_types.py           tipos de arquivo reconhecidos (extensão -> tipo e cor)
    images.py               prepara a foto do cartão (corta e reduz)
    cloud.py                acha Google Drive, OneDrive e Dropbox no PC
    office.py               descobre arquivos abertos no Excel/Word
    excel.py                salva e fecha no Excel as planilhas do painel (backup pelo botão)
    updater.py              procura versão nova no GitHub, baixa e troca o .exe
    opener.py, shortcuts.py abrir arquivos/sites e criar atalho na Área de Trabalho
    paths.py                onde cada pasta fica
  ui/                       TELA (CustomTkinter)
    main_window.py          janela principal e as ações dos botões
    theme.py                cores, fontes e medidas (o visual inteiro está aqui)
    art.py                  desenhos: capas com bolhas, selos e a logo do Bar do Sabão
    widgets/                cabeçalho, filtros, grade, cartão, barra de backup, aviso, faixa de atualização
    dialogs/                editar cartão, adicionar, configurações, mensagens
    notification.py         aviso no canto da tela do backup automático
  silent.py                 modo backup sem janela (o que roda toda semana)
assets/                     ícone e fonte do título
empacotamento/              receita do PyInstaller e informações do .exe
testes/                     testes automáticos das regras
ferramentas/                dados de exemplo, captura das telas e publicar versão
CLAUDE.md                   guia do código para o Claude Code
```

### Mudanças comuns

- **Cores e tamanhos:** `app/ui/theme.py`. Cada cor tem a versão clara e a escura.
- **Reconhecer uma extensão nova** (ex.: `.ofx` como planilha):
  `EXTENSIONS` em `app/core/file_types.py`.
- **Novo campo no cartão:** acrescente em `Item` (`app/core/models.py`).
  Configurações antigas continuam abrindo, porque campos ausentes usam o padrão.
- **Nova versão do programa:** use o `publicar_versao.bat` (veja abaixo).
  Ele troca o número sozinho.

### Publicar uma versão nova (atualização nos outros computadores)

O código fica no GitHub (github.com/FilipeNsdev/painel-do-bar). Cada versão
publicada leva o `PainelDoBar.exe` junto. Os painéis instalados perguntam ao
GitHub, ao abrir, se tem versão nova. Se tiver, aparece uma faixa escura
embaixo do cabeçalho: **"Versão 1.2.0 disponível"** e o botão
**Atualizar agora**. O painel baixa, fecha, troca o .exe e abre de novo. A
pasta `Dados` não é tocada.

Para publicar, depois de testar a mudança:

1. Dois cliques em `publicar_versao.bat`.
2. Digite o número novo, maior que o atual. Mudança pequena: 1.1.0 vira
   1.1.1. Novidade: 1.1.0 vira 1.2.0.
3. Escreva numa frase o que mudou. É o texto que aparece na faixa.

Ele roda os testes, gera o .exe, grava no Git, envia para o GitHub e cria a
versão. Se algo falhar antes do envio, nada é publicado e o número volta.

Rodando pelo código (sem ser o .exe), o painel nunca oferece atualização.

### Testar alterações

```
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

Para abrir o painel direto do código, sem gerar o .exe:
dois cliques em `abrir_pelo_codigo.bat`.

Para ver todas as telas com dados de exemplo (sem tocar nos dados reais):

```
.venv\Scripts\python ferramentas\capturar_telas.py
```

As imagens vão para a pasta `capturas`. O `CLAUDE.md` explica o projeto para
quem for mexer no código (inclusive o Claude Code).

## 6. Problemas comuns

- **"O backup automático não ligou":** o Windows precisa permitir criar
  tarefas agendadas. Em computador de empresa, isso pode estar bloqueado.
- **Mudei o .exe de pasta:** abra o painel uma vez no lugar novo. Ele
  atualiza o backup semanal sozinho. A pasta `Dados` precisa ir junto.
- **Algo deu errado:** em **Configurações > Painel > Abrir os registros**,
  o arquivo `painel.log` tem o detalhe técnico.

---

Fonte do título: *Alfa Slab One*, licença SIL Open Font License (ver `assets/fontes/OFL.txt`).
