@echo off
setlocal
cd /d "%~dp0"
title Suzano Aberta - Instalacao Windows

echo ============================================================
echo                    SUZANO ABERTA
echo             Instalacao para Windows / CMD
echo ============================================================
echo.

set "PYTHON="
where py >nul 2>nul && set "PYTHON=py -3"
if not defined PYTHON (
  where python >nul 2>nul && set "PYTHON=python"
)
if not defined PYTHON (
  echo ERRO: Python 3.11 ou superior nao foi encontrado no PATH.
  echo Instale o Python e execute este arquivo novamente.
  pause
  exit /b 1
)

%PYTHON% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" || (
  echo ERRO: Suzano Aberta requer Python 3.11 ou superior.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Criando ambiente virtual...
  %PYTHON% -m venv .venv || goto :erro
) else (
  echo [1/4] Ambiente virtual ja existe.
)

echo [2/4] Atualizando instalador Python...
".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :erro

echo [3/4] Instalando Suzano Aberta...
".venv\Scripts\python.exe" -m pip install -e . || goto :erro

echo [4/4] Verificando CLI...
".venv\Scripts\python.exe" -m suzano_aberta.cli --help >nul || goto :erro

echo.
echo Instalacao concluida.
echo.
echo Agora voce pode usar:
echo   suzano.cmd
echo.
echo Ou executar comandos diretamente:
echo   suzano.cmd buscar "educacao"
echo   suzano.cmd panorama
echo   suzano.cmd sincronizar
echo   suzano.cmd fontes
echo.
echo Abrindo o console interativo...
echo.
call suzano.cmd
exit /b 0

:erro
echo.
echo A instalacao nao foi concluida. Veja a mensagem acima.
pause
exit /b 1
