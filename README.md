# RPG Audio Toolkit

Suíte de três aplicativos desktop independentes (Windows, Python + PySide6)
para organizar músicas e efeitos sonoros de campanhas de RPG, funcionando
100% localmente — sem servidor, conta ou assinatura.

```text
Internet / arquivos locais
    ↓
RPG Audio Downloader          (planejado — Etapa 5)
    ↓
Biblioteca geral de músicas
    ↓
RPG Soundtrack Manager        (Etapas 2 e 3 prontas)
    ↓
Soundtrack organizada de uma campanha

Biblioteca de efeitos sonoros
    ↓
RPG SFX Manager                (planejado — Etapa 4)
    ↓
Coleções/packs de SFX para campanhas
```

## Os três aplicativos

Cada um é um programa independente, com seu próprio executável e propósito
claro — não é uma suíte com abas.

| App | Pasta | Função | Status |
|---|---|---|---|
| RPG Audio Downloader | `downloader/` | Baixar áudio (yt-dlp + FFmpeg) e organizar em pastas | Planejado |
| **RPG Soundtrack Manager** | `soundtrack-manager/` | Biblioteca de músicas, player, tags, campanhas, soundtracks com seções, modo triagem, duplicados, exportação | **Etapas 2 e 3 prontas** |
| RPG SFX Manager | `sfx-manager/` | Biblioteca de efeitos sonoros, reprodução rápida, packs de SFX | Planejado |

## Arquitetura adotada

- **Linguagem/UI:** Python 3.11 + PySide6 (Qt), tema escuro próprio (paleta +
  QSS), sem depender de frameworks pesados de UI.
- **Persistência:** SQLite local por app (um banco por aplicativo, já que
  cada um tem seu próprio domínio de dados) — sem servidor, sem nuvem própria.
  Pastas do Google Drive/OneDrive/Dropbox são tratadas como pastas locais
  normais.
- **Arquivos de áudio:** nunca são copiados, movidos ou renomeados pela
  biblioteca — o banco só guarda metadados e classificações apontando para o
  caminho original. Cópia só acontece explicitamente ao exportar uma
  soundtrack/pack.
- **Concorrência:** escaneamento de biblioteca roda em `QThread` própria,
  comunicando com a UI só por signals/slots (nunca manipula widgets a partir
  de outra thread), para lidar com bibliotecas de milhares de arquivos sem
  travar a interface.
- **Separação em camadas** (dentro de cada app): `ui/` (widgets/diálogos) →
  `services/` (scanner, player, exportação — lógica de aplicação) →
  `repositories/` (SQL) → `database/` (schema/conexão). Modelos são
  `dataclasses` simples em `models/`.
- **Reuso entre apps:** `shared/rpg_audio_shared` — sanitização de caminhos
  para Windows, hashing de arquivos (identificação robusta a pequenas
  reorganizações), leitura de metadados de áudio (mutagen), tema Qt
  compartilhado e formatação. Instalado em modo editável por cada app; cada
  app continua rodando e sendo empacotado (`.exe`) de forma independente.

## Começando (RPG Soundtrack Manager)

**No Windows:** entre na pasta `soundtrack-manager` e dê dois cliques em
`ABRIR.bat` — ele instala tudo sozinho na primeira vez.

**Linha de comando (qualquer sistema):**

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r soundtrack-manager/requirements.txt
cd soundtrack-manager && python main.py
```

Veja [`soundtrack-manager/README.md`](soundtrack-manager/README.md) para
detalhes (instruções completas de teste no Windows, testes automatizados,
estrutura, banco de dados, atalhos).

## Roadmap

1. ~~Arquitetura da suíte~~ ✅
2. ~~RPG Soundtrack Manager — MVP~~ ✅ (biblioteca, scanner, banco, player,
   busca, favoritos, tags, soundtrack com salvamento automático, exportação)
3. ~~Soundtrack Manager — experiência avançada~~ ✅ (modo triagem, seções de
   soundtrack, exportação com seções, histórico, aleatório, filtro "não
   avaliadas", campanhas na UI, detector de duplicados, arquivos ausentes)
4. RPG SFX Manager
5. RPG Audio Downloader
6. Build dos três executáveis Windows (PyInstaller)
