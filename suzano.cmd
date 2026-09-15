@echo off
setlocal
cd /d "%~dp0"

set "PYTHON="
where py >nul 2>nul && set "PYTHON=py -3"
if not defined PYTHON (
  where python >nul 2>nul && set "PYTHON=python"
)

if not defined PYTHON (
  echo.
  echo [Suzano Aberta] Python 3.11 ou superior nao foi encontrado.
  echo Instale o Python e marque a opcao para adiciona-lo ao PATH.
  echo.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [Suzano Aberta] Preparando ambiente local pela primeira vez...
  %PYTHON% -m venv .venv || exit /b 1
  ".venv\Scripts\python.exe" -m pip install --upgrade pip || exit /b 1
  ".venv\Scripts\python.exe" -m pip install -e . || exit /b 1
)

if "%~1"=="" (
  ".venv\Scripts\python.exe" -m suzano_aberta.cli console
) else (
  ".venv\Scripts\python.exe" -m suzano_aberta.cli %*
)
