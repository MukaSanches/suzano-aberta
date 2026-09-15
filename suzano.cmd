@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Suzano Aberta

set "VENV_PY=.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
  echo [Suzano Aberta] Ambiente local ainda nao esta instalado.
  echo [Suzano Aberta] Executando instalacao automatica...
  call "%~dp0instalar-windows.cmd" --no-open
  if errorlevel 1 exit /b %errorlevel%
)

if "%~1"=="" (
  "%VENV_PY%" -m suzano_aberta.console
) else if /I "%~1"=="console" (
  "%VENV_PY%" -m suzano_aberta.console
) else (
  "%VENV_PY%" -m suzano_aberta.cli %*
)

exit /b %errorlevel%
