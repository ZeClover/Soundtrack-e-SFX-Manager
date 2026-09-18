@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   RPG Audio Studio - Build Windows (Etapa 6)
echo ============================================================
echo.
echo IMPORTANTE: isto so gera um .exe de verdade quando rodado NUM
echo WINDOWS de verdade. O PyInstaller nao faz cross-compile - rodar
echo isto num Linux/Mac gera um binario daquele sistema, nao um .exe.
echo.

if not exist "..\soundtrack-manager\soundtrack_app" (
    echo [ERRO] Nao encontrei a pasta "soundtrack-manager" ao lado desta.
    echo O build precisa do repositorio inteiro ^(shared, soundtrack-manager,
    echo sfx-manager e rpg-audio-studio juntas^).
    pause
    exit /b 1
)
if not exist "..\sfx-manager\sfx_app" (
    echo [ERRO] Nao encontrei a pasta "sfx-manager" ao lado desta.
    pause
    exit /b 1
)

rem ------------------------------------------------------------------
rem 1) Ambiente: reusa o .venv do projeto (mesma logica do INSTALAR.bat),
rem    e garante que pyinstaller + pillow tambem estao instalados nele -
rem    sao so ferramentas de build, nao vao pro requirements.txt do app.
rem ------------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual nao encontrado em ".venv".
    echo Rode INSTALAR.bat primeiro.
    pause
    exit /b 1
)

set PY=".venv\Scripts\python.exe"

echo Instalando/atualizando dependencias do app...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias. Veja a mensagem acima.
    pause
    exit /b 1
)

echo Instalando ferramentas de build ^(pyinstaller, pyinstaller-hooks-contrib, pillow^)...
%PY% -m pip install "pyinstaller>=6.0" "pyinstaller-hooks-contrib" "pillow"
if errorlevel 1 (
    echo [ERRO] Falha ao instalar as ferramentas de build.
    pause
    exit /b 1
)

rem ------------------------------------------------------------------
rem 2) Testes primeiro - nunca gerar uma distribuicao em cima de codigo
rem    quebrado. Roda a suite dos quatro pacotes (shared + os tres apps).
rem ------------------------------------------------------------------
echo.
echo ============================================================
echo   Rodando os testes automatizados antes do build...
echo ============================================================
%PY% -m pytest -q ..\shared\tests
if errorlevel 1 goto :tests_failed
%PY% -m pytest -q ..\soundtrack-manager\tests
if errorlevel 1 goto :tests_failed
%PY% -m pytest -q ..\sfx-manager\tests
if errorlevel 1 goto :tests_failed
%PY% -m pytest -q tests
if errorlevel 1 goto :tests_failed

echo.
echo Todos os testes passaram - build pode continuar.
goto :tests_ok

:tests_failed
echo.
echo [ERRO] Os testes automatizados falharam. O build foi CANCELADO -
echo nao faz sentido distribuir um programa com testes quebrados.
pause
exit /b 1

:tests_ok

rem ------------------------------------------------------------------
rem 3) Icone e metadados do .exe (a partir de app/version.py).
rem ------------------------------------------------------------------
echo.
if not exist "assets\icon.ico" (
    echo Gerando icone do aplicativo...
    %PY% scripts\generate_icon.py
)

echo Gerando metadados do executavel ^(version_info.txt^)...
%PY% scripts\generate_version_info.py
if errorlevel 1 (
    echo [ERRO] Falha ao gerar version_info.txt.
    pause
    exit /b 1
)

rem ------------------------------------------------------------------
rem 4) FFmpeg empacotado (opcional, mas recomendado): se o usuario ja
rem    colocou ffmpeg.exe/ffprobe.exe em rpg-audio-studio\ffmpeg\, o
rem    .spec inclui na distribuicao. Se nao, so avisa e segue - o app
rem    cai pro FFmpeg do PATH do sistema em tempo de execucao.
rem ------------------------------------------------------------------
echo.
if exist "ffmpeg\ffmpeg.exe" if exist "ffmpeg\ffprobe.exe" (
    echo FFmpeg encontrado em ffmpeg\ - sera incluido na distribuicao.
) else (
    echo [AVISO] ffmpeg\ffmpeg.exe / ffprobe.exe nao encontrados.
    echo A distribuicao vai sair SEM FFmpeg empacotado - MP3 so vai
    echo funcionar em maquinas que ja tem FFmpeg no PATH do sistema.
    echo Para empacotar: baixe uma build estatica do FFmpeg para Windows
    echo ^(https://www.gyan.dev/ffmpeg/builds/ - "essentials" ja basta^)
    echo e coloque ffmpeg.exe e ffprobe.exe em "rpg-audio-studio\ffmpeg\".
)

rem ------------------------------------------------------------------
rem 5) Limpa builds anteriores e roda o PyInstaller.
rem ------------------------------------------------------------------
echo.
echo Limpando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo ============================================================
echo   Empacotando com PyInstaller...
echo ============================================================
%PY% -m PyInstaller RPGAudioStudio.spec --noconfirm
if errorlevel 1 (
    echo [ERRO] O PyInstaller falhou. Veja a mensagem acima.
    pause
    exit /b 1
)

if not exist "dist\RPG Audio Studio\RPG Audio Studio.exe" (
    echo [ERRO] O PyInstaller terminou mas o .exe esperado nao apareceu em
    echo dist\RPG Audio Studio\RPG Audio Studio.exe - build considerado FALHO.
    pause
    exit /b 1
)

echo.
echo Build gerado em: dist\RPG Audio Studio\
echo.
echo LEMBRETE: "PyInstaller terminou sem erro" nao e a mesma coisa que
echo "o programa funciona". Abra "dist\RPG Audio Studio\RPG Audio Studio.exe"
echo agora e navegue por todas as telas antes de distribuir.
echo.

rem ------------------------------------------------------------------
rem 6) Empacota o ZIP final + checksum SHA256 (release/).
rem ------------------------------------------------------------------
for /f "delims=" %%v in ('%PY% -c "import sys; sys.path.insert(0, '.'); from app.version import APP_VERSION; print(APP_VERSION)"') do set APP_VERSION=%%v

if not exist "release" mkdir "release"
set ZIP_NAME=RPG-Audio-Studio-v%APP_VERSION%-Windows.zip
set ZIP_PATH=release\%ZIP_NAME%

echo Gerando %ZIP_PATH% ...
if exist "%ZIP_PATH%" del "%ZIP_PATH%"
powershell -NoProfile -Command "Compress-Archive -Path 'dist\RPG Audio Studio' -DestinationPath '%ZIP_PATH%'"
if errorlevel 1 (
    echo [ERRO] Falha ao gerar o ZIP.
    pause
    exit /b 1
)

echo Gerando checksum SHA256...
powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 '%ZIP_PATH%').Hash + '  %ZIP_NAME%'" > "%ZIP_PATH%.sha256"

echo.
echo ============================================================
echo   Build concluido!
echo ============================================================
echo   Pasta portatil:  dist\RPG Audio Studio\
echo   ZIP de release:  %ZIP_PATH%
echo   Checksum:        %ZIP_PATH%.sha256
echo.
echo   Para usar: extraia o ZIP em qualquer lugar e rode
echo   "RPG Audio Studio.exe" - nao precisa instalar nada.
echo ============================================================
pause
