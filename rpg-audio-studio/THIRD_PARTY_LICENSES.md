# Licenças de terceiros

O RPG Audio Studio é construído sobre bibliotecas e ferramentas de código
aberto. Esta página lista as principais, seus papéis no programa e onde
encontrar os textos oficiais das respectivas licenças — **não é um
parecer jurídico**, só uma referência factual para quem for redistribuir
o programa. Se você pretende redistribuir isto comercialmente em escala,
consulte um profissional para confirmar a conformidade com cada licença
listada abaixo.

## Bibliotecas Python (empacotadas dentro do `.exe`)

| Componente | Uso no projeto | Licença | Mais informações |
|---|---|---|---|
| **Qt / PySide6** | Toda a interface gráfica (janelas, widgets, temas, player de áudio via `QtMultimedia`) | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only (o projeto usa a opção **LGPL-3.0**, que permite uso em programas fechados desde que o Qt em si continue trocável/relincável) | <https://www.qt.io/licensing/> · <https://doc.qt.io/qt-6/lgpl.html> |
| **yt-dlp** | Motor de download do módulo Downloader (extrai e baixa vídeos/playlists) | Unlicense (equivalente a domínio público) | <https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE> |
| **mutagen** | Leitura de metadados de áudio (duração, tags) ao escanear a biblioteca | GPL-2.0-or-later | <https://github.com/quodlibet/mutagen/blob/main/COPYING> |
| **PyInstaller** | Não é uma dependência do código do app — é a ferramenta que empacota o `.exe`; seu *bootloader* (pequeno programa que inicia o Python empacotado) fica embutido no executável final | GPLv2-or-later, **com uma exceção explícita** que permite usá-lo para empacotar e distribuir programas não-livres, incluindo comerciais | <https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt> |
| **Pillow** | Só em tempo de build (`scripts/generate_icon.py`), não fica embutida no `.exe` final — gera os arquivos `icon.ico`/`icon.png` uma vez, que aí sim são distribuídos como imagens | MIT-CMU (variante permissiva do MIT) | <https://github.com/python-pillow/Pillow/blob/main/LICENSE> |

## FFmpeg / FFprobe (binário externo, empacotado opcionalmente)

O RPG Audio Studio **não redistribui o código-fonte do FFmpeg** — ele usa
o FFmpeg como um programa externo (chamado via linha de comando), seja
uma cópia empacotada junto do `.exe` (pasta `ffmpeg/`, se o build incluiu
uma) ou uma instalação já existente no PATH do sistema do usuário.

A licença exata do FFmpeg **depende de como o binário específico foi
compilado**:

- A maioria das builds "essentials"/padrão para Windows (ex.: as
  distribuídas por <https://www.gyan.dev/ffmpeg/builds/> ou
  <https://www.ffmpeg.org/download.html>) é licenciada como
  **LGPL v2.1 ou posterior**.
- Builds com certos componentes extras habilitados (ex.: `--enable-gpl`,
  codecs específicos) passam a ser **GPL v2 ou posterior**.

Ao empacotar uma cópia do FFmpeg junto do `.exe` (via `BUILD_WINDOWS.bat`
+ pasta `ffmpeg/`), confirme qual licença a build específica que você
baixou declara (normalmente num arquivo `LICENSE`/`readme` junto do
download) e mantenha esse arquivo junto da distribuição. Texto completo
das licenças: <https://www.ffmpeg.org/legal.html>.

## Sobre este projeto

O código-fonte deste projeto (RPG Audio Studio, RPG Soundtrack Manager,
RPG SFX Manager e o pacote `shared`) já está disponível neste mesmo
repositório — não há nenhum componente de terceiros aqui cujo uso dependa
de esconder o código-fonte do próprio projeto.
