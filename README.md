# RPG Audio Toolkit

**RPG Audio Studio**: aplicativo desktop único (Windows, Python + PySide6)
para baixar, organizar e tocar músicas e efeitos sonoros de campanhas de
RPG — funcionando 100% localmente, sem servidor, conta ou assinatura.

```text
YouTube / arquivos locais
    ↓
Downloader
    ↓
Biblioteca de músicas
    ↓
Soundtracks

Biblioteca de efeitos sonoros
    ↓
Packs de SFX
```

Tudo dentro da mesma janela — o usuário não abre três programas
diferentes. Internamente a suíte continua modular: cada parte vive num
módulo separado, com seu próprio banco de dados e sua própria lógica, só a
**experiência do usuário** é unificada.

## O produto

| Módulo | Pasta | Função | Status |
|---|---|---|---|
| **RPG Audio Studio** | `rpg-audio-studio/` | Shell principal — Home, Música/Soundtracks, SFX/Packs, Downloader, Histórico, Configurações | **v1.0.0 — build e distribuição prontos** |
| RPG Soundtrack Manager | `soundtrack-manager/` | Módulo de música/soundtracks (embutido no Studio; também roda sozinho) | Etapas 2 e 3 prontas |
| RPG SFX Manager | `sfx-manager/` | Módulo de efeitos/packs (embutido no Studio; também roda sozinho) | Etapa 4 pronta |

**Para usar o programa pronto:** baixe o `.zip` da versão mais recente
(veja `rpg-audio-studio/README.md`), extraia e rode
`RPG Audio Studio.exe` — não precisa instalar Python nem nada além disso.
As instruções abaixo são para quem for **desenvolver/rodar a partir do
código-fonte**.

`soundtrack-manager/` e `sfx-manager/` não são mais "produtos finais"
separados — são os módulos que o RPG Audio Studio embute. Eles continuam
podendo rodar sozinhos durante desenvolvimento/depuração (veja abaixo),
mas o app que o usuário final abre é o **RPG Audio Studio**.

## Arquitetura adotada

- **Linguagem/UI:** Python 3.11 + PySide6 (Qt), tema escuro próprio (paleta +
  QSS), sem depender de frameworks pesados de UI.
- **Shell + módulos, não monolito:** o RPG Audio Studio (`rpg-audio-studio/`)
  é uma janela com navegação lateral que **importa o código-fonte** dos
  módulos Música e SFX diretamente (pacotes `soundtrack_app`/`sfx_app`) e os
  embute como páginas — a lógica de negócio desses dois módulos não foi
  reescrita, só deixou de montar sua própria `QMainWindow` isolada para virar
  um `QWidget` reaproveitável tanto no app standalone quanto no Studio.
- **Persistência:** SQLite local por módulo (`soundtrack_manager.db`,
  `sfx_manager.db`, e um banco bem pequeno próprio do Studio só para
  preferências que não pertencem a nenhum módulo) — sem servidor, sem nuvem
  própria, sem centralizar tudo artificialmente num banco só. Pastas do
  Google Drive/OneDrive/Dropbox são tratadas como pastas locais normais.
- **Arquivos de áudio:** nunca são copiados, movidos ou renomeados pela
  biblioteca — o banco só guarda metadados e classificações apontando para o
  caminho original. Cópia só acontece explicitamente ao exportar uma
  soundtrack/pack, ou ao baixar algo novo pelo Downloader.
- **Concorrência:** escaneamento de biblioteca e downloads rodam em `QThread`
  própria, comunicando com a UI só por signals/slots (nunca manipulando
  widgets a partir de outra thread), para lidar com bibliotecas de milhares
  de arquivos e playlists grandes sem travar a interface.
- **Inicialização preguiçosa:** cada página do Studio (Música, SFX,
  Downloader...) só é criada na primeira vez que o usuário navega até ela, e
  fica em cache depois — navegar repetidamente entre páginas não recria
  scanners, players ou conexões de banco duplicadas.
- **Separação em camadas** (dentro de cada módulo): `ui/` (widgets/diálogos) →
  `services/` (scanner, player, exportação, download — lógica de aplicação) →
  `repositories/` (SQL) → `database/` (schema/conexão). Modelos são
  `dataclasses` simples em `models/`.
- **Reuso entre módulos:** `shared/rpg_audio_shared` — sanitização de
  caminhos para Windows, hashing de arquivos, leitura de metadados de áudio
  (mutagen), tema Qt compartilhado, formatação, logging e uma proteção
  contra `sys.stdout`/`stderr` serem `None` (caso de `pythonw.exe` sem
  console, que já causou um bug real no Downloader antigo).

## Começando

**No Windows:** entre na pasta `rpg-audio-studio` e dê dois cliques em
`ABRIR.bat` — ele instala tudo sozinho na primeira vez (as pastas
`shared/`, `soundtrack-manager/` e `sfx-manager/` precisam estar ao lado
dela; é o repositório inteiro, não só uma pasta).

**Linha de comando (qualquer sistema):**

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r rpg-audio-studio/requirements.txt
cd rpg-audio-studio && python main.py
```

Veja [`rpg-audio-studio/README.md`](rpg-audio-studio/README.md) para
detalhes completos (instalação da versão portátil, build do `.exe`,
testes automatizados, estrutura, dados/backup, recursos) e
[`rpg-audio-studio/GUIA-RAPIDO.md`](rpg-audio-studio/GUIA-RAPIDO.md) para
um passo a passo simples de como usar o programa.

### Rodar um módulo isolado (desenvolvimento)

Continua funcionando, se for útil para depurar algo específico:

```bash
python soundtrack-manager/main.py
python sfx-manager/main.py
```

Usam o mesmo banco de dados que usariam dentro do Studio.

## Roadmap

1. ~~Arquitetura da suíte~~ ✅
2. ~~RPG Soundtrack Manager — MVP~~ ✅ (biblioteca, scanner, banco, player,
   busca, favoritos, tags, soundtrack com salvamento automático, exportação)
3. ~~Soundtrack Manager — experiência avançada~~ ✅ (modo triagem, seções de
   soundtrack, exportação com seções, histórico, aleatório, filtro "não
   avaliadas", campanhas na UI, detector de duplicados, arquivos ausentes)
4. ~~RPG SFX Manager~~ ✅ (biblioteca com categorias automáticas, cards/lista,
   reprodução simultânea, hotkeys, packs, detector de duplicados, arquivos
   ausentes, exportação)
5. ~~RPG Audio Studio — unificação + Downloader~~ ✅ (shell único reaproveitando
   os módulos Música e SFX, RPG Audio Downloader novo com yt-dlp + FFmpeg,
   integração Downloader → Biblioteca, configurações unificadas, backup/
   restauração, histórico consolidado)
6. ~~Build final + polimento + distribuição Windows~~ ✅ (executável único
   via PyInstaller, FFmpeg/yt-dlp funcionando empacotados, ícone e
   metadados do `.exe`, primeira execução opcional, mensagens de erro
   amigáveis, logs com rotação, `BUILD_WINDOWS.bat` reproduzível, release
   em `.zip` + checksum SHA256, README/guia rápido/licenças finais — ver
   `rpg-audio-studio/README.md` para o relatório completo)
