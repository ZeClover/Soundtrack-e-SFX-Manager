@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Primeira vez executando o programa: instalando dependencias...
    echo.
    call "%~dp0INSTALAR.bat"
    if errorlevel 1 (
        exit /b 1
    )
)

echo Iniciando RPG Audio Studio...
echo.
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo ============================================================
    echo   O programa fechou com um erro. Veja a mensagem acima.
    echo   Se o problema persistir, apague a pasta ".venv" nesta pasta
    echo   e execute INSTALAR.bat novamente.
    echo ============================================================
    pause
)
