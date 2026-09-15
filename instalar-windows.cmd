@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Suzano Aberta - Instalacao
chcp 65001 >nul 2>nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "NO_OPEN=0"
set "REPAIR=0"

:parse_args
if "%~1"=="" goto :args_done
if /I "%~1"=="--no-open" set "NO_OPEN=1"
if /I "%~1"=="--repair" set "REPAIR=1"
shift
goto :parse_args

:args_done
echo ============================================================
echo                     SUZANO ABERTA
echo          Instalacao verificada para Windows / CMD
echo ============================================================
echo.

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 (
  for %%V in (3.13 3.12 3.11) do (
    if not defined PY_CMD (
      py -%%V -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
      if not errorlevel 1 set "PY_CMD=py -%%V"
    )
  )
)

if not defined PY_CMD (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 set "PY_CMD=python"
  )
)

if not defined PY_CMD goto :python_missing

echo [1/7] Python compativel encontrado:
%PY_CMD% --version
if errorlevel 1 goto :error

if "%REPAIR%"=="1" if exist ".venv" (
  echo [2/7] Removendo ambiente virtual anterior para reparo limpo...
  rmdir /s /q ".venv"
  if exist ".venv" goto :error
) else (
  echo [2/7] Reparo nao solicitado.
)

if not exist ".venv\Scripts\python.exe" (
  echo [3/7] Criando ambiente virtual isolado...
  %PY_CMD% -m venv .venv
  if errorlevel 1 goto :error
) else (
  echo [3/7] Ambiente virtual existente sera reutilizado.
)

echo [4/7] Atualizando ferramentas de instalacao...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [5/7] Instalando Suzano Aberta e dependencias declaradas...
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto :error

echo [6/7] Compilando o pacote para detectar erros de sintaxe...
".venv\Scripts\python.exe" -m compileall -q src
if errorlevel 1 goto :error

echo [7/7] Executando smoke tests do produto...
".venv\Scripts\python.exe" -m suzano_aberta.cli --help >nul
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -c "from suzano_aberta.console import parse_command, resolve_reference; from suzano_aberta.diagnostics import inspect_local_environment; assert parse_command('b educacao')[0] == 'buscar'; assert resolve_reference('1', []) == '1'; inspect_local_environment('suzano-aberta.sqlite3')"
if errorlevel 1 goto :error

echo.
echo ============================================================
echo  Instalacao validada com sucesso.
echo ============================================================
echo.
echo Abra a experiencia interativa com:
echo   suzano.cmd
echo.
echo Se algum dia o ambiente virtual quebrar:
echo   suzano.cmd reparar
echo.
echo Comandos diretos continuam disponiveis:
echo   suzano.cmd buscar "educacao"
echo   suzano.cmd panorama
echo   suzano.cmd sincronizar
echo   suzano.cmd doctor
echo.

if "%NO_OPEN%"=="1" exit /b 0
call "%~dp0suzano.cmd"
exit /b %errorlevel%

:python_missing
echo ERRO: Python 3.11, 3.12 ou 3.13 nao foi encontrado.
echo Instale uma versao compativel e habilite o launcher py ou o Python no PATH.
exit /b 1

:error
echo.
echo ERRO: a instalacao foi interrompida porque uma verificacao falhou.
echo Nenhuma etapa posterior sera apresentada como concluida.
echo Para uma reinstalacao limpa, execute: instalar-windows.cmd --repair
exit /b 1
