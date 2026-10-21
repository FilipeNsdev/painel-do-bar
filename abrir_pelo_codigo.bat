@echo off
rem Abre o painel direto do codigo, sem gerar o .exe.
rem Bom para testar alteracoes. Rode o gerar_exe.bat antes, uma vez,
rem para criar o ambiente (.venv) com as bibliotecas.
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Rode primeiro o gerar_exe.bat para preparar o ambiente.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" main.py
