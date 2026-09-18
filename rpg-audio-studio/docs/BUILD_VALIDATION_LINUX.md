# Build de validação em Linux (Etapa 6, item 66)

## O que isto é — e o que NÃO é

Este ambiente de desenvolvimento roda Linux. **O PyInstaller não faz
cross-compile**: rodar `pyinstaller RPGAudioStudio.spec` aqui produz um
binário ELF do Linux, nunca um `.exe` do Windows. Isso não é uma
limitação do `.spec` ou do processo — é uma limitação de como o
PyInstaller funciona em qualquer projeto.

O que foi feito aqui serve como **prova de que o `.spec` e o código do app
estão corretos o bastante para virar um executável funcional** — hidden
imports resolvidos, dados empacotados no lugar certo, caminhos de
dados/log corretos, e o app abrindo e fechando sem travar. O `.exe`
Windows de verdade só sai rodando `BUILD_WINDOWS.bat` numa máquina ou CI
Windows real, com esse mesmo `.spec`.

## Comando usado

```bash
python -m PyInstaller RPGAudioStudio.spec --noconfirm
```

## Resultado do empacotamento

- Build concluído sem erros. Único aviso relevante:
  `WARNING: Ignoring version information; supported only on Windows!` e
  `WARNING: Ignoring icon; supported only on Windows and macOS!` — exatamente
  o esperado: confirma que o `.spec` está passando `version=` e `icon=`
  corretamente, e que essas duas opções são no-op aqui só porque o SO é
  Linux (no Windows elas vão ser aplicadas de verdade).
- Avisos de bibliotecas `libxcb-icccm`/`libxcb-keysyms` não resolvidas: são
  dependências do plugin de plataforma gráfica do Linux (`libqxcb.so`) —
  irrelevantes no Windows, que usa um plugin de plataforma totalmente
  diferente.
- Saída: `dist/RPG Audio Studio/RPG Audio Studio` (binário ELF) +
  `dist/RPG Audio Studio/_internal/` (~208 MB no total, incluindo Qt/
  PySide6 completo — tamanho esperado antes de qualquer compressão de
  release).
- `assets/icon.ico` e `assets/icon.png` confirmados presentes em
  `dist/RPG Audio Studio/_internal/assets/` — os dados extras do `.spec`
  foram copiados corretamente.

## Smoke test do executável gerado

Rodado com `QT_QPA_PLATFORM=offscreen` (sem display gráfico neste
ambiente) e `HOME` apontando pra uma pasta temporária isolada, pra não
misturar com nenhum dado real.

1. **Primeira execução** — `HOME` vazio, sem `first_run_completed`
   salvo. O app abriu, inicializou logging, e ficou parado no diálogo de
   primeira execução (comportamento correto e esperado — item 15: nunca
   aparece sem intenção, e bloqueia esperando decisão do usuário, exatamente
   como os testes automatizados de `test_welcome_dialog.py`/
   `test_first_run.py` já garantem). Nenhum traceback, nenhum crash.
2. Confirmado que os arquivos de dados corretos foram criados em
   `~/.rpg-audio-toolkit/` (equivalente Linux do `%APPDATA%` do Windows,
   resolvido por `rpg_audio_shared/app_dirs.py`), **fora** da pasta de
   extração do PyInstaller:
   - `rpg-audio-studio/studio_settings.db` (+ `-wal`/`-shm`, confirmando
     modo WAL ativo)
   - `rpg-audio-studio/logs/app-*.log`, `soundtrack-*.log`, `sfx-*.log`,
     `downloader-*.log` (item 28 — um arquivo por módulo, todos criados)
   - `sfx-manager/sfx_manager.db`
   - `soundtrack-manager/soundtrack_manager.db`
3. **Segunda execução**, com `first_run_completed` pré-marcado no banco
   (simulando um usuário que já passou pela primeira execução): o app
   passa direto pro loop principal sem travar em nenhum diálogo modal.
4. **Encerramento com `SIGTERM`** enviado diretamente ao processo real do
   binário (identificado por PID, não pelo wrapper do shell): o processo
   termina em ~2 segundos, sem travar, sem precisar de `SIGKILL`.
5. **Teste de integridade sob término abrupto** (pior caso, mais hostil
   que fechar a janela normalmente): processo morto com `SIGKILL` enquanto
   rodava, com o banco de configurações do Studio já tendo gerado arquivos
   `-wal`/`-shm` (evidência de escrita em andamento). Reabrindo o banco
   depois:
   ```
   PRAGMA integrity_check;  -- ok
   ```
   Confirma o item 25: o SQLite em modo WAL sobrevive a um encerramento
   inesperado sem corrupção, sem precisar de nenhum código extra de
   "recuperação de crash" no app — a garantia vem do próprio modo de
   jornalamento do SQLite.
6. Nenhum processo `ffmpeg` ou instância órfã do app ficou rodando depois
   de qualquer um dos testes acima.

## O que isto NÃO valida (só um Windows real valida)

- Ícone aparecendo de fato na barra de título/taskbar e no `.exe` (a opção
  é ignorada no Linux, como mostrado acima).
- Metadados do executável (Product Name, File Description, Company,
  Version) visíveis nas propriedades do arquivo no Explorer.
- `pythonw.exe`/modo sem console de verdade (aqui não existe essa
  distinção — Linux não tem o conceito de subsistema Windows/console).
- FFmpeg empacotado (nenhum `ffmpeg.exe`/`ffprobe.exe` do Windows estava
  disponível neste ambiente Linux pra testar — ver `YTDLP_UPDATE_STRATEGY.md`
  e a seção de FFmpeg do README pra como isso é resolvido no build real).
- Teste manual do Downloader baixando de verdade (ver relatório final da
  Etapa 6 pra status de conectividade deste ambiente).

Essas lacunas são inerentes a rodar isto fora do Windows, e estão documentadas
aqui em vez de escondidas — não foram fabricadas nem presumidas como
"provavelmente funciona".
