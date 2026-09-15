@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Suzano Aberta

rem UTF-8 consistente para Rich, acentos e o prompt moderno no Windows Terminal/CMD.
chcp 65001 >nul 2>nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "VENV_PY=.venv\Scripts\python.exe"

if /I "%~1"=="instalar" (
  call "%~dp0instalar-windows.cmd"
  exit /b %errorlevel%
)

if /I "%~1"=="reparar" (
  call "%~dp0instalar-windows.cmd" --repair
  exit /b %errorlevel%
)

if not exist "%VENV_PY%" (
  echo [Suzano Aberta] Preparando o ambiente local pela primeira vez...
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

set "EXIT_CODE=%errorlevel%"
exit /b %EXIT_CODE%
