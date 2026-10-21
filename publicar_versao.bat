@echo off
rem Publica uma versao nova do Painel do Bar no GitHub.
rem Os paineis instalados oferecem a atualizacao quando abrirem.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Rode o gerar_exe.bat uma vez antes.
  pause
  exit /b 1
)
echo.
for /f "delims=" %%v in ('.venv\Scripts\python -c "from app import __version__; print(__version__)"') do set ATUAL=%%v
echo  Versao atual: %ATUAL%
echo.
set /p NOVA= Numero da versao nova (ex.: 1.1.0): 
set /p NOTAS= O que mudou (uma frase): 
echo.
.venv\Scripts\python ferramentas\publicar_versao.py "%NOVA%" "%NOTAS%"
echo.
pause
