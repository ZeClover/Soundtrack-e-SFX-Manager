@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   RPG Audio Studio - Instalacao
echo ============================================================
echo.

if not exist "..\soundtrack-manager\soundtrack_app" (
    echo [ERRO] Nao encontrei a pasta "soundtrack-manager" ao lado desta.
    echo O RPG Audio Studio precisa do repositorio inteiro baixado/clonado
    echo ^(as pastas shared, soundtrack-manager, sfx-manager e rpg-audio-studio
    echo devem estar todas juntas^) — nao copie so esta pasta.
    echo.
    pause
    exit /b 1
)
if not exist "..\sfx-manager\sfx_app" (
    echo [ERRO] Nao encontrei a pasta "sfx-manager" ao lado desta.
    echo O RPG Audio Studio precisa do repositorio inteiro baixado/clonado.
    echo.
    pause
    exit /b 1
)

set PYTHON_CMD=

where python >nul 2>nul
if not errorlevel 1 (
    set PYTHON_CMD=python
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        set PYTHON_CMD=py
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERRO] Python nao foi encontrado no PATH.
    echo.
    echo Instale o Python 3.10 ou mais recente em:
    echo     https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: na tela de instalacao do Python, marque a opcao
    echo "Add python.exe to PATH" antes de clicar em Install.
    echo.
    pause
    exit /b 1
)

echo Python encontrado: %PYTHON_CMD%
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual em ".venv"...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar o ambiente virtual.
        pause
        exit /b 1
    )
)

echo Instalando dependencias ^(pode demorar alguns minutos na primeira vez^)...
echo Isso inclui tudo que os tres modulos ^(Musica, SFX, Downloader^) precisam.
echo.
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao instalar as dependencias. Veja a mensagem acima.
    pause
    exit /b 1
)

echo.
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo [AVISO] FFmpeg nao foi encontrado no PATH.
    echo Isso NAO impede o programa de abrir, escanear, tocar musicas/efeitos
    echo ou baixar do YouTube. Ele so e necessario para converter para MP3
    echo ^(ao exportar uma soundtrack/pack, ou ao baixar em MP3 no Downloader^).
    echo Se precisar, baixe em https://ffmpeg.org/download.html e adicione
    echo a pasta "bin" dele ao PATH do Windows.
    echo.
)

echo ============================================================
echo   Instalacao concluida!
echo   Use o arquivo ABRIR.bat para iniciar o RPG Audio Studio.
echo ============================================================
echo.
pause
