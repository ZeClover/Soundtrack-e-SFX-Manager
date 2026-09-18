# RPG Audio Studio

Aplicativo único para Windows que reúne toda a suíte **RPG Audio Toolkit**
numa só janela: baixar músicas do YouTube, organizar a biblioteca musical
em soundtracks, e organizar efeitos sonoros em packs — sem precisar abrir
três programas separados, sem instalar Python, sem instalar nada além do
próprio programa.

Parte da suíte **RPG Audio Toolkit** (veja o [README da raiz](../README.md)).

## O que é

Um programa de mesa de RPG local (sem servidor, sem conta, sem
assinatura) com três frentes, todas na mesma janela:

- **Downloader** — cola a URL de um vídeo ou playlist do YouTube e baixa
  em MP3 (com nível de qualidade) ou no melhor áudio original.
- **Música e Soundtracks** — organiza sua biblioteca de músicas em
  soundtracks por campanha/sessão, com busca, favoritos, tags, seções,
  modo triagem (avaliar músicas rapidamente por teclado), histórico e
  exportação.
- **SFX e Packs** — organiza efeitos sonoros em packs, com categorias
  automáticas por pasta, reprodução simultânea (chuva + trovão + passos ao
  mesmo tempo, por exemplo) e hotkeys.

Um **player global** na parte de baixo da janela continua tocando e
visível mesmo trocando de página. **Configurações** reúne tudo num só
lugar, sem duplicar preferências. **Backup/Restauração** salva/recupera
todos os seus dados (nunca os arquivos de áudio em si, só os bancos —
tags, soundtracks, packs, histórico, configurações). **Histórico** junta
músicas, efeitos e downloads recentes numa única página.

## Instalar e usar (Windows, versão portátil)

Não tem instalador — é só extrair e rodar:

1. Baixe o arquivo `RPG-Audio-Studio-vX.Y.Z-Windows.zip` do release.
2. Extraia em qualquer pasta (Área de Trabalho, Documentos, um pendrive —
   onde quiser).
3. Abra a pasta extraída e dê dois cliques em **`RPG Audio Studio.exe`**.

Não precisa de Python, não precisa de internet pra instalar (só quando for
usar o Downloader), e não precisa de permissão de administrador. Seus
dados (bibliotecas, soundtracks, packs, configurações, logs) ficam em
`%LOCALAPPDATA%\RPG Audio Toolkit\` — apagar/mover a pasta do programa
**não apaga seus dados**, e reinstalar uma versão nova por cima **não
perde nada**.

Veja o [`GUIA-RAPIDO.md`](GUIA-RAPIDO.md) para um passo a passo simples,
sem termos técnicos, de como usar o programa pela primeira vez.

### FFmpeg

O FFmpeg é usado só para converter pra MP3 (na exportação de uma
soundtrack/pack, ou ao baixar em MP3 no Downloader) — o resto do programa
funciona sem ele. O `.zip` de release pode ou não trazer o FFmpeg junto,
dependendo de como aquele build específico foi gerado (veja
`YTDLP_UPDATE_STRATEGY.md` e `BUILD_WINDOWS.bat` para os detalhes de
build). Se o programa avisar que o FFmpeg não foi encontrado, baixe uma
build para Windows em <https://www.ffmpeg.org/download.html> (ou
<https://www.gyan.dev/ffmpeg/builds/>, "essentials" já basta) e adicione a
pasta `bin` dela ao PATH do Windows — depois disso o programa encontra o
FFmpeg sozinho, sem precisar reconfigurar nada dentro dele.

## Solução de problemas

- **"FFmpeg não encontrado" ao exportar/baixar em MP3** — veja a seção
  FFmpeg acima. O resto do programa (biblioteca, player, packs, downloads
  em áudio original) continua funcionando normalmente sem ele.
- **Uma pasta configurada (música/SFX) não existe mais** — o programa
  avisa e deixa escolher a pasta de novo, sem travar nem perder o que já
  estava catalogado das outras pastas.
- **O programa fechou/travou** — os bancos de dados usam um modo do
  SQLite (WAL) que sobrevive a fechamentos inesperados sem corromper; é
  seguro simplesmente abrir o programa de novo. Se algo parecer errado,
  `Configurações → Backup` sempre tem uma cópia de segurança pra
  restaurar.
- **Erro genérico numa caixa de diálogo** — clique em "Show Details..."
  (se aparecer) para ver o detalhe técnico, ou veja o arquivo de log
  correspondente em `%LOCALAPPDATA%\RPG Audio Toolkit\rpg-audio-studio\logs\`
  (um arquivo por módulo: `app-*.log`, `soundtrack-*.log`, `sfx-*.log`,
  `downloader-*.log`).
- **Quero voltar para uma versão antiga dos meus dados** — use
  `Configurações → Restaurar backup` com um `.zip` de backup salvo
  anteriormente.

## Arquitetura

Este app **não é um monolito nem uma reescrita** dos outros dois módulos.
Ele importa diretamente o código-fonte de `soundtrack-manager/` e
`sfx-manager/` (pacotes `soundtrack_app` e `sfx_app`) e os embute como
páginas de um shell comum — a lógica de negócio, os repositórios, os
serviços e os testes desses dois módulos continuam exatamente onde
sempre estiveram, sem duplicação.

```text
rpg-audio-studio/
    main.py                    # raiz de composição: monta o shell + liga os módulos
    version.py (app/version.py) # fonte única de verdade da versão
    ABRIR.bat / INSTALAR.bat    # uso em desenvolvimento (roda a partir do código-fonte)
    BUILD_WINDOWS.bat           # gera o executável distribuível (ver "Build" abaixo)
    RPGAudioStudio.spec         # configuração do PyInstaller
    app/
        shell/                  # janela principal genérica: navegação lateral + páginas + player global
        settings/                # banco/config próprios do Studio + tela de Configurações unificada
        backup/                  # backup/restauração (zip dos bancos, nunca dos áudios)
        bootstrap.py             # coloca soundtrack-manager/ e sfx-manager/ no sys.path
        config.py                # caminhos de recursos (frozen-aware) vs. caminhos de dados do usuário
    modules/
        soundtrack/page.py       # embute soundtrack_app.ui.main_window.MainWindow como página
        sfx/page.py               # embute sfx_app.ui.main_window.MainWindow como página
        downloader/               # yt-dlp + FFmpeg
            services/               # DownloadWorker (QThread), logger próprio, archive, ffmpeg check
            ui/                      # página do Downloader
        home/                     # Home com estatísticas e ações rápidas
        history/                  # histórico unificado (música + SFX + downloads)
    scripts/
        generate_icon.py          # gera assets/icon.ico + icon.png
        generate_version_info.py  # gera version_info.txt (metadados do .exe) a partir de app/version.py
    tests/
```

Cada módulo continua rodável sozinho durante o desenvolvimento (veja
"Executar os módulos isolados" abaixo) — o Studio só adiciona uma casca em
volta deles.

## Desenvolver (rodar a partir do código-fonte)

**No Windows:** entre na pasta `rpg-audio-studio` e dê dois cliques em
`ABRIR.bat` (instala tudo sozinho na primeira vez).

**Linha de comando (qualquer sistema):**

```bash
# a partir da raiz do repositório
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r rpg-audio-studio/requirements.txt
cd rpg-audio-studio
python main.py
```

Pré-requisito: **Python 3.10 ou mais recente**
([python.org/downloads](https://www.python.org/downloads/)), marcando
**"Add python.exe to PATH"** na instalação. O `FFmpeg` é opcional em
desenvolvimento também — só necessário para conversão pra MP3.

### Executar os módulos isolados (compatibilidade)

Durante desenvolvimento/depuração, cada módulo continua abrindo sozinho,
com sua própria janela:

```bash
python soundtrack-manager/main.py
python sfx-manager/main.py
```

Eles usam o mesmo banco de dados que usariam dentro do Studio — abrir um
ou outro não duplica nem perde dados (veja "Dados e backup" abaixo).

## Testes

```bash
cd rpg-audio-studio
pytest
```

Junto com `shared/tests`, `soundtrack-manager/tests` e `sfx-manager/tests`,
a suíte inteira do projeto cobre: navegação do shell, integração real dos
módulos Música e SFX dentro do shell, o serviço do Downloader inteiro com
yt-dlp mockado (playlist, item que falha sem abortar o resto, cancelamento,
archive de já-baixados, FFmpeg ausente), configurações unificadas,
backup/restauração, histórico consolidado, segurança de encerramento
(fechar o app com scanner/player/download em andamento não trava nem
lança), detecção de app empacotado (frozen) vs. desenvolvimento, resolução
do FFmpeg empacotado com fallback pro PATH, versão/metadados, e a
pré-seleção da preferência de conflito de exportação. Os testes de
`soundtrack-manager/` e `sfx-manager/` continuam existindo e passando
normalmente — nada foi removido.

## Build (executável Windows)

O executável distribuível é gerado com **PyInstaller**, em formato
**one-folder** (uma pasta com o `.exe` e os arquivos de apoio ao lado —
mais estável e mais fácil de depurar que "um arquivo só", que precisa
extrair tudo pra uma pasta temporária a cada abertura).

**Em uma máquina Windows** (o PyInstaller não faz cross-compile — isto
precisa rodar num Windows de verdade para gerar um `.exe` de verdade):

```bat
cd rpg-audio-studio
BUILD_WINDOWS.bat
```

O script:

1. Confere se `soundtrack-manager/` e `sfx-manager/` estão presentes.
2. Instala/atualiza as dependências do app e as ferramentas de build
   (`pyinstaller`, `pyinstaller-hooks-contrib`, `pillow`) no `.venv`.
3. Roda a suíte de testes inteira — **cancela o build se algum teste
   falhar**.
4. Gera o ícone (se ainda não existir) e o `version_info.txt` (metadados
   do `.exe`, a partir de `app/version.py`).
5. Empacota com PyInstaller usando `RPGAudioStudio.spec`.
6. Confirma que `dist\RPG Audio Studio\RPG Audio Studio.exe` realmente
   existe (não considera "o PyInstaller não deu erro" como sucesso).
7. Gera o `.zip` final em `release\RPG-Audio-Studio-vX.Y.Z-Windows.zip` +
   um checksum `.sha256` ao lado.

FFmpeg empacotado (opcional, mas recomendado para quem for redistribuir):
coloque `ffmpeg.exe` e `ffprobe.exe` numa pasta `rpg-audio-studio\ffmpeg\`
antes de rodar o `BUILD_WINDOWS.bat` — o `.spec` detecta e inclui
automaticamente. Sem essa pasta, o build sai normalmente e o app cai pro
FFmpeg do PATH do sistema do usuário final.

Depois do build, **abra o `.exe` gerado e navegue pelo programa antes de
distribuir** — "o PyInstaller terminou" não é a mesma coisa que "o
programa funciona".

Veja `docs/BUILD_VALIDATION_LINUX.md` para o que já foi validado (e o que
só um Windows real consegue validar) sobre este processo de build.

## Dados e backup

Os dados do usuário (bibliotecas, soundtracks, packs, tags, histórico,
configurações, logs) sempre ficam na pasta de dados do usuário do Windows
(`%APPDATA%`/`%LOCALAPPDATA%`), **nunca** dentro da pasta onde o programa
foi instalado/extraído — apagar ou mover a pasta do programa não apaga
seus dados, e trocar de versão do programa não exige nenhuma migração:
```
%APPDATA%\RPG Audio Toolkit\
    soundtrack-manager\soundtrack_manager.db
    sfx-manager\sfx_manager.db
    rpg-audio-studio\
        studio_settings.db      # preferências que não pertencem a nenhum módulo específico
        logs\
            app-AAAA-MM-DD.log
            soundtrack-AAAA-MM-DD.log
            sfx-AAAA-MM-DD.log
            downloader-AAAA-MM-DD.log
```

Os arquivos de áudio em si **nunca são copiados, movidos ou renomeados**
pela biblioteca — o banco só guarda metadados/classificações apontando
para o caminho original. Isso também significa que uma pasta sincronizada
pelo OneDrive/Google Drive/Dropbox funciona normalmente: pro programa ela
é só uma pasta local comum.

`Configurações → Backup` gera um `.zip` com os bancos de dados (nunca com
os arquivos de áudio, que tendem a ser grandes demais e já estão seguros
nas pastas originais) — use `Restaurar backup` para recuperar.

## Recursos

- **Home**: contadores rápidos (músicas, soundtracks, SFX, packs) e atalhos
  para as ações mais comuns.
- **Música e Soundtracks**: biblioteca completa do Soundtrack Manager —
  scanner, busca, favoritos, tags, campanhas, observações, modo triagem,
  histórico, aleatório, seções de soundtrack, duplicados, arquivos ausentes
  e exportação (com conversão opcional para MP3).
- **SFX e Packs**: biblioteca completa do SFX Manager — cards/lista,
  categorias automáticas, reprodução simultânea, hotkeys, packs,
  duplicados e arquivos ausentes.
- **Downloader**: cola a URL de um vídeo ou playlist do YouTube, escolhe
  MP3 (com qualidade) ou melhor áudio original, pasta de destino, opção de
  subpasta por playlist e numeração; mostra progresso item a item (com
  velocidade/ETA), um log recolhível com mensagens amigáveis, cancelamento
  seguro, e nunca aborta a playlist inteira por causa de um vídeo com
  problema. Depois de baixar, oferece adicionar/atualizar a biblioteca.
- **Player global**: uma barra de player na parte inferior do Studio
  (reaproveitando o `PlayerBar` do Soundtrack Manager) continua tocando e
  visível mesmo navegando para outras páginas.
- **Primeira execução**: uma tela opcional (sempre com "Pular por
  enquanto") pra já apontar as pastas de música/SFX/downloads — nunca
  obrigatória, nunca reaparece depois.
- **Sobre**: em Configurações, mostra a versão instalada e os três
  módulos que compõem o programa.
- **Configurações**: uma tela só, com seções por módulo, sem duplicar
  nenhuma preferência que já mora no banco de um módulo específico.
- **Backup/Restauração**: veja "Dados e backup" acima.
- **Histórico**: músicas, efeitos e downloads recentes numa única página.

## Licenças de terceiros

Este programa é feito com bibliotecas de código aberto — veja
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) para a lista e os
termos de cada uma (Qt/PySide6, FFmpeg, yt-dlp e as demais).

## Limitações conhecidas

- Neste repositório de desenvolvimento (ambiente Linux, sem acesso geral à
  internet), não foi possível gerar nem testar o `.exe` real do Windows,
  nem baixar de verdade pelo Downloader — ver o relatório da Etapa 6 e
  `docs/BUILD_VALIDATION_LINUX.md` para exatamente o que foi validado por
  um build de proxy em Linux e o que precisa ser confirmado uma vez num
  Windows real.
