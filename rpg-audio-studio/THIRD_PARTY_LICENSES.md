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

## FFmpeg / FFprobe (binário externo, empacotado no build oficial)

O RPG Audio Studio **não redistribui o código-fonte do FFmpeg** — ele usa
o FFmpeg como um programa externo (chamado via linha de comando), a
partir de uma cópia empacotada junto do `.exe` (pasta `ffmpeg/`) ou,
apenas em desenvolvimento, de uma instalação já existente no PATH do
sistema.

**Origem da cópia empacotada nos releases oficiais do Windows:**
`BUILD_WINDOWS.bat` baixa automaticamente, via `scripts/fetch_ffmpeg.py`,
a build **"release essentials"** do FFmpeg para Windows mantida por Gyan
Doshi:

- URL: <https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip>
- Esta é uma das duas fontes de build para Windows **oficialmente
  recomendadas na própria página de download do FFmpeg**
  (<https://www.ffmpeg.org/download.html#build-windows>, junto com o
  BtbN).
- **Licença: GPLv3.** O próprio gyan.dev declara que "all builds are
  64-bit, static and licensed as GPLv3", e o zip traz um `LICENSE.txt`
  (copiado do repositório do FFmpeg) — esse arquivo é preservado junto do
  download, e uma cópia dos termos completos está disponível em
  <https://www.ffmpeg.org/legal.html>.
- `fetch_ffmpeg.py` confere o checksum SHA256 do download contra
  `ffmpeg-release-essentials.zip.sha256` (publicado pelo mesmo gyan.dev)
  antes de extrair e usar os binários — download corrompido ou adulterado
  faz o script (e o build inteiro) falhar, em vez de seguir em frente.

Se você preferir usar uma build LGPL (para evitar as obrigações do GPL
numa redistribuição fechada) ou qualquer outra fonte, basta colocar
manualmente `ffmpeg.exe`/`ffprobe.exe` em `rpg-audio-studio/ffmpeg/` antes
de rodar `BUILD_WINDOWS.bat` — o script detecta que já existem binários
válidos e não baixa por cima; nesse caso, confirme a licença que a build
escolhida declara (normalmente num `LICENSE`/`readme` junto do download) e
mantenha esse arquivo junto da distribuição.

## Sobre este projeto

O código-fonte deste projeto (RPG Audio Studio, RPG Soundtrack Manager,
RPG SFX Manager e o pacote `shared`) já está disponível neste mesmo
repositório — não há nenhum componente de terceiros aqui cujo uso dependa
de esconder o código-fonte do próprio projeto.
