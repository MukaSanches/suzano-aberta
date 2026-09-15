@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Suzano Aberta - Instalacao

set "NO_OPEN=0"
if /I "%~1"=="--no-open" set "NO_OPEN=1"

 echo ============================================================
 echo                     SUZANO ABERTA
 echo              Instalacao para Windows / CMD
 echo ============================================================
 echo.

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if not defined PY_CMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)
if not defined PY_CMD goto :python_missing

%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 goto :python_old

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Criando ambiente virtual isolado...
  %PY_CMD% -m venv .venv
  if errorlevel 1 goto :error
) else (
  echo [1/5] Ambiente virtual encontrado.
)

echo [2/5] Atualizando pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [3/5] Instalando Suzano Aberta e dependencias...
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto :error

echo [4/5] Validando dependencias...
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto :error

echo [5/5] Executando testes rapidos de inicializacao...
".venv\Scripts\python.exe" -m suzano_aberta.cli --help >nul
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -c "from suzano_aberta.console import parse_command; assert parse_command('buscar educacao')[0] == 'buscar'"
if errorlevel 1 goto :error

echo.
echo ============================================================
echo  Instalacao concluida com sucesso.
echo ============================================================
echo.
echo Para abrir o programa:
echo   suzano.cmd
echo.
echo Para usar comandos diretos:
echo   suzano.cmd buscar "educacao"
echo   suzano.cmd panorama
echo   suzano.cmd sincronizar
echo   suzano.cmd fontes
echo.

if "%NO_OPEN%"=="1" exit /b 0
call "%~dp0suzano.cmd"
exit /b %errorlevel%

:python_missing
echo ERRO: Python nao foi encontrado.
echo Instale Python 3.11 ou superior e habilite a opcao Add Python to PATH.
exit /b 1

:python_old
echo ERRO: e necessario Python 3.11 ou superior.
exit /b 1

:error
echo.
echo ERRO: a instalacao foi interrompida porque uma verificacao falhou.
echo Revise a mensagem exibida acima e tente novamente.
exit /b 1
