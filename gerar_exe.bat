@echo off
setlocal
cd /d "%~dp0"
title Gerando o Painel do Bar

echo.
echo  ==========================================================
echo    Gerando o PainelDoBar.exe
echo    Na primeira vez leva alguns minutos, porque baixa as
echo    bibliotecas. Nas proximas e bem mais rapido.
echo  ==========================================================
echo.

rem --- Procura um Python com Tkinter --------------------------------------
rem Prefere o 3.13 (o mais testado com o CustomTkinter); depois 3.12 e 3.14.
set "PY="
for %%V in (3.13 3.12 3.14 3.11) do (
  if not defined PY (
    py -%%V -c "import tkinter" >nul 2>nul && set "PY=py -%%V"
  )
)
if not defined PY (
  python -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
  py -c "import sys" >nul 2>nul && goto :sem_tkinter
  python -c "import sys" >nul 2>nul && goto :sem_tkinter
  goto :sem_python
)
echo  Usando o Python:
%PY% -c "import sys, tkinter; print('   ', sys.version.split()[0], '/ Tk', tkinter.TkVersion)"
echo.

rem --- Ambiente isolado so para este projeto ------------------------------
if not exist ".venv\Scripts\python.exe" (
  echo  Criando o ambiente do projeto...
  %PY% -m venv .venv
  if errorlevel 1 goto :erro
)

echo  Instalando as bibliotecas...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller --quiet
if errorlevel 1 goto :erro

echo  Montando o executavel...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --log-level WARN --distpath dist --workpath build empacotamento\PainelDoBar.spec
if errorlevel 1 goto :erro

echo.
echo  ==========================================================
echo    PRONTO! O programa esta em:
echo    %cd%\dist\PainelDoBar.exe
echo.
echo    Proximo passo: crie a pasta C:\PainelDoBar, copie o
echo    PainelDoBar.exe para dentro dela e abra. Ele cria a
echo    pasta "Dados" ao lado dele na primeira vez.
echo  ==========================================================
echo.
start "" explorer "%cd%\dist"
pause
exit /b 0

:sem_python
echo  [ERRO] Nao encontrei o Python instalado.
echo.
echo  1. Baixe o Python em https://www.python.org/downloads/windows/
echo  2. Na instalacao, marque "Add python.exe to PATH"
echo  3. Rode este arquivo de novo
echo.
pause
exit /b 1

:sem_tkinter
echo  [ERRO] Encontrei o Python, mas sem o Tkinter, que desenha as janelas.
echo.
echo  Baixe o Python 3.13 em https://www.python.org/downloads/windows/
echo  escolhendo o "Windows installer 64-bit", e deixe marcada a opcao
echo  "tcl/tk and IDLE" durante a instalacao. Depois rode este arquivo de novo.
echo.
pause
exit /b 1

:erro
echo.
echo  [ERRO] Algo deu errado. Leia as mensagens acima, ou mande
echo  uma foto desta tela para quem esta te ajudando.
echo.
pause
exit /b 1
