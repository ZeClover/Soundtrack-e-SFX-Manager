# RPG Audio Studio

Aplicativo único que reúne toda a suíte RPG Audio Toolkit numa só janela:
baixar músicas do YouTube, organizar a biblioteca musical em soundtracks e
organizar efeitos sonoros em packs — sem precisar abrir três programas
separados.

Parte da suíte **RPG Audio Toolkit** (veja o [README da raiz](../README.md)).

## Status

Etapa 5 do roadmap do projeto concluída: shell principal com navegação
lateral (Home, Música e Soundtracks, SFX e Packs, Downloader, Histórico,
Configurações), reaproveitando 100% da lógica já existente do RPG
Soundtrack Manager e do RPG SFX Manager como módulos embutidos, mais o
RPG Audio Downloader novo (yt-dlp + FFmpeg), integração Downloader →
Biblioteca, configurações unificadas, backup/restauração e histórico
consolidado.

## Arquitetura

Este app **não é um monolito nem uma reescrita** dos outros dois. Ele
importa diretamente o código-fonte de `soundtrack-manager/` e
`sfx-manager/` (pacotes `soundtrack_app` e `sfx_app`) e os embute como
páginas de um shell comum — a lógica de negócio, os repositórios, os
serviços e os testes desses dois módulos continuam exatamente onde
sempre estiveram, sem duplicação.

```text
rpg-audio-studio/
    main.py                    # raiz de composição: monta o shell + liga os módulos
    ABRIR.bat / INSTALAR.bat
    app/
        shell/                  # janela principal genérica: navegação lateral + páginas + player global
        settings/                # banco/config próprios do Studio + tela de Configurações unificada
        backup/                  # backup/restauração (zip dos bancos, nunca dos áudios)
        bootstrap.py             # coloca soundtrack-manager/ e sfx-manager/ no sys.path
        config.py
    modules/
        soundtrack/page.py       # embute soundtrack_app.ui.main_window.MainWindow como página
        sfx/page.py               # embute sfx_app.ui.main_window.MainWindow como página
        downloader/               # módulo novo desta etapa (yt-dlp + FFmpeg)
            services/               # DownloadWorker (QThread), logger próprio, archive, ffmpeg check
            ui/                      # página do Downloader
        home/                     # Home com estatísticas e ações rápidas
        history/                  # histórico unificado (música + SFX + downloads)
    tests/
```

Cada módulo continua rodável sozinho durante o desenvolvimento (veja
"Executar os módulos isolados" abaixo) — o Studio só adiciona uma casca em
volta deles.

## COMO TESTAR NO WINDOWS

1. Baixe/clone o repositório inteiro (as pastas `shared/`,
   `soundtrack-manager/` e `sfx-manager/` precisam estar ao lado de
   `rpg-audio-studio/` — não copie só esta pasta).
2. Abra a pasta `rpg-audio-studio`.
3. Dê **dois cliques em `ABRIR.bat`**.
   - Na primeira vez, ele instala tudo sozinho (cria um ambiente Python
     isolado em `.venv` e baixa as dependências dos três módulos de uma
     vez) — pode demorar alguns minutos.
   - Nas próximas vezes, `ABRIR.bat` já abre o programa direto.
4. Se preferir instalar manualmente antes, dê dois cliques em
   `INSTALAR.bat` primeiro.

Pré-requisito: **Python 3.10 ou mais recente**
([python.org/downloads](https://www.python.org/downloads/)), marcando
**"Add python.exe to PATH"** na instalação. O `FFmpeg` é opcional — só é
necessário para converter para MP3 (na exportação ou no Downloader); sem
ele, o resto do programa funciona normalmente.

## Instalação (desenvolvimento)

```bash
# a partir da raiz do repositório
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r rpg-audio-studio/requirements.txt
```

## Executar em desenvolvimento

```bash
cd rpg-audio-studio
python main.py
```

## Executar os módulos isolados (compatibilidade)

Durante desenvolvimento/depuração, cada módulo continua abrindo sozinho,
com sua própria janela:

```bash
python soundtrack-manager/main.py
python sfx-manager/main.py
```

Eles usam o mesmo banco de dados que usariam dentro do Studio — abrir um
ou outro não duplica nem perde dados (veja "Dados e migração" abaixo).

## Testes

```bash
cd rpg-audio-studio
pytest
```

Cobre: navegação do shell (páginas criadas sob demanda, só uma vez cada,
flag de "módulo ativo" liga/desliga nos atalhos), integração real dos
módulos Música e SFX dentro do shell, o serviço do Downloader inteiro com
yt-dlp mockado (playlist, item que falha sem abortar o resto, cancelamento,
archive de já-baixados, FFmpeg ausente), a página do Downloader, a
integração Downloader → Biblioteca, configurações unificadas,
backup/restauração e o histórico consolidado. Os testes de
`soundtrack-manager/` e `sfx-manager/` continuam existindo e passando
normalmente — nada foi removido.

## Build (executável Windows)

Planejado para a Etapa 6 do projeto (PyInstaller). Ainda não implementado.

## Dados e migração

Nenhum dado existente é perdido. O Studio usa os **mesmos bancos SQLite**
que os apps standalone sempre usaram
(`%APPDATA%\RPG Audio Toolkit\soundtrack-manager\...` e
`...\sfx-manager\...`) — só o Studio em si guarda algumas preferências
novas (pasta padrão de downloads, formato/qualidade preferidos, tema) num
banco próprio bem pequeno, `...\rpg-audio-studio\studio_settings.db`, sem
duplicar nada que já morava nos outros dois.

## Recursos

- **Home**: contadores rápidos (músicas, soundtracks, SFX, packs) e atalhos
  para as ações mais comuns.
- **Música e Soundtracks**: biblioteca completa do Soundtrack Manager —
  scanner, busca, favoritos, tags, campanhas, observações, modo triagem,
  histórico, aleatório, seções de soundtrack, duplicados, arquivos ausentes
  e exportação.
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
- **Configurações**: uma tela só, com seções por módulo, sem duplicar
  nenhuma preferência que já mora no banco de um módulo específico.
- **Backup/Restauração**: gera um `.zip` com os bancos (músicas, tags,
  soundtracks, SFX, packs, histórico, configurações) — nunca com os
  arquivos de áudio — e restaura com confirmação.
- **Histórico**: músicas, efeitos e downloads recentes numa única página.

## Limitações conhecidas

- A preferência "comportamento de duplicados na exportação" (Configurações
  → Exportação) fica salva no Studio, mas ainda não é aplicada como valor
  pré-selecionado automaticamente dentro dos diálogos de exportação do
  Soundtrack Manager/SFX Manager (que continuam pedindo a escolha a cada
  exportação, como sempre fizeram) — fica para um polimento futuro.
- Build final em `.exe` fica para a Etapa 6, como planejado.
