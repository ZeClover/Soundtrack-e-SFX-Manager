# RPG Soundtrack Manager

Organiza uma biblioteca de músicas (de qualquer tamanho, sem duplicar arquivos)
em soundtracks para campanhas de RPG: favoritar, marcar tags, ouvir com um
player integrado e exportar a soundtrack final para uma pasta própria — sem
nunca mover, renomear ou apagar os arquivos originais.

Parte da suíte **RPG Audio Toolkit** (veja o [README da raiz](../README.md)).

## Status

Etapas 2 e 3 do roadmap do projeto concluídas: biblioteca, scanner, busca,
favoritos, tags, campanhas, observações, soundtrack com seções opcionais
(criar/adicionar/reordenar/remover, mover músicas entre seções) e
salvamento automático, player integrado, modo triagem, histórico de
reprodução, botão aleatório, filtro "não avaliadas", detector de
duplicados, tratamento de arquivos ausentes e exportação (com ou sem
seções, em subpastas ou lista única).

## COMO TESTAR NO WINDOWS

Forma mais simples, sem usar linha de comando:

1. Baixe/clone o repositório inteiro (a pasta `shared/` ao lado de
   `soundtrack-manager/` é necessária — não copie só esta pasta).
2. Abra a pasta `soundtrack-manager`.
3. Dê **dois cliques em `ABRIR.bat`**.
   - Na primeira vez, ele instala tudo sozinho (cria um ambiente Python
     isolado em `.venv` e baixa as dependências) — pode demorar alguns
     minutos e vai pedir para apertar uma tecla ao final da instalação.
   - Nas próximas vezes, `ABRIR.bat` já abre o programa direto.
4. Se preferir instalar manualmente antes (ou reinstalar do zero após
   apagar a pasta `.venv`), dê dois cliques em `INSTALAR.bat` primeiro.

Pré-requisito: **Python 3.10 ou mais recente** instalado
([python.org/downloads](https://www.python.org/downloads/)), marcando a
opção **"Add python.exe to PATH"** durante a instalação do Python. O
`FFmpeg` é opcional — só é necessário se você usar "Converter tudo para
MP3" ao exportar uma soundtrack; sem ele, o resto do programa funciona
normalmente (o `ABRIR.bat`/`INSTALAR.bat` avisam se ele não for encontrado).

Se algo der errado: apague a pasta `.venv` (dentro de `soundtrack-manager`)
e rode `INSTALAR.bat` novamente.

## Instalação (desenvolvimento)

Requer Python 3.10+ e [FFmpeg](https://ffmpeg.org/download.html) instalado e
disponível no PATH (usado apenas para converter para MP3 na exportação — a
reprodução e o escaneamento não precisam dele).

```bash
# a partir da raiz do repositório
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r soundtrack-manager/requirements.txt
```

O `requirements.txt` já instala o pacote `shared/` (`rpg_audio_shared`) em
modo editável — não é preciso instalar nada manualmente ali.

## Executar em desenvolvimento

```bash
cd soundtrack-manager
python main.py
```

## Testes

```bash
cd soundtrack-manager
pytest
```

Os testes rodam em modo *headless* (`QT_QPA_PLATFORM=offscreen`, configurado
automaticamente em `tests/conftest.py`) e cobrem: scanner de biblioteca,
hashing/identificação de arquivos, sanitização de nomes para Windows,
repositórios do banco (incluindo seções de soundtrack), exportação
(numeração, conflitos, conversão, seções em subpastas), navegação de
playlist do player, escolha aleatória sem repetição imediata, detector de
duplicados (confirmado/possível) e os diálogos de triagem e histórico.
Alguns testes que dependem do `ffmpeg` são pulados automaticamente se ele
não estiver disponível.

## Build (executável Windows)

Planejado para a Etapa 6 do projeto (PyInstaller, um `.exe` por app). Ainda
não implementado nesta fase.

## Estrutura

```text
soundtrack-manager/
    ABRIR.bat                # Windows: instala (1a vez) e abre o programa
    INSTALAR.bat              # Windows: instala/reinstala as dependências
    main.py                  # ponto de entrada (python main.py)
    app/
        config.py             # caminhos e constantes do app
        database/              # schema SQL + wrapper de conexão SQLite
        models/                 # dataclasses (Track, Soundtrack, Tag, Campaign...)
        repositories/            # acesso ao banco (uma classe por entidade)
        services/                # scanner (QThread), player, exportação, duplicados, aleatório
        ui/
            main_window.py        # orquestra os painéis e a lógica da app
            widgets/                # painéis: filtros, biblioteca, soundtrack (com seções), player
            dialogs/                # exportar, triagem, histórico, duplicados, campanhas, progresso do scan
    tests/                    # pytest (banco, scanner, exportação, UI)
```

`shared/rpg_audio_shared` (na raiz do monorepo) concentra o que é comum aos
três apps da suíte: sanitização de caminhos, hashing, leitura de metadados
de áudio, tema escuro Qt e utilitários de formatação.

## Banco de dados

SQLite local em `%APPDATA%\RPG Audio Toolkit\soundtrack-manager\soundtrack_manager.db`
no Windows (em outros sistemas, usado apenas em desenvolvimento, cai em
`~/.rpg-audio-toolkit/soundtrack-manager/`). Principais tabelas:
`tracks`, `tags` / `track_tags`, `campaigns` / `track_campaigns`,
`soundtracks`, `soundtrack_sections`, `soundtrack_items`, `play_history`,
`settings`, `library_roots`.

A biblioteca **nunca** copia, move ou renomeia os arquivos de áudio
originais — o banco apenas guarda metadados e classificações (favorito,
tags, observação) apontando para o caminho original. Um rescan detecta
arquivos novos e marca como "ausente" (sem apagar do banco) os que
sumiram, sem reprocessar metadados de arquivos já conhecidos.

## Configurações

A pasta da biblioteca selecionada é lembrada automaticamente (tabela
`settings`) e recarregada na próxima abertura do programa. Soundtracks são
salvas a cada alteração — não existe um botão "Salvar".

## Atalhos de teclado

Na janela principal, funcionam apenas quando o foco não está em um campo de texto.

| Tecla     | Ação                                  |
|-----------|----------------------------------------|
| `Espaço`  | Play / Pause                           |
| `Enter`   | Adicionar música selecionada à soundtrack |
| `F`       | Favoritar / desfavoritar               |
| `↑` / `↓` | Navegar pela lista da biblioteca        |

No **Modo Triagem** (botão "Modo Triagem" ao lado da busca):

| Tecla     | Ação                    |
|-----------|--------------------------|
| `Espaço`  | Play / Pause             |
| `←` / `→` | Música anterior / próxima |
| `A`       | Adicionar à soundtrack atual |
| `F`       | Favoritar / desfavoritar |

## Recursos avançados (Etapa 3)

- **Seções de soundtrack**: botão "＋ Seção" no painel direito; clique com o
  botão direito em um cabeçalho de seção para renomear, mover ou remover
  (remover uma seção não apaga as músicas, só as desagrupa). Arrastar uma
  música para debaixo de outro cabeçalho move ela para aquela seção.
- **Exportação com seções**: ao exportar uma soundtrack que tem seções, é
  possível escolher entre tudo em uma pasta só ou uma subpasta por seção.
- **Modo Triagem**: botão ao lado da busca — toca a lista atual (respeitando
  os filtros ligados) em tela cheia, com atalhos para decidir rápido.
- **Histórico**: botão "🕘 Histórico" na barra de ferramentas mostra as
  últimas músicas ouvidas.
- **Aleatório**: botão "🎲 Aleatório" toca uma música aleatória entre as que
  estão filtradas no momento, evitando repetir as últimas tocadas.
- **Campanhas**: associe uma música a uma ou mais campanhas no campo
  "Campanhas" (como as tags); crie/renomeie/apague campanhas em "Gerenciar..."
  no painel de filtros.
- **Detector de duplicados**: botão "Localizar duplicados" na barra de
  ferramentas. Nunca remove nada sozinho — mostra os grupos (confirmado por
  hash, ou possível por nome/tamanho/duração) para você decidir.
- **Arquivos ausentes**: clique com o botão direito numa música marcada como
  ausente para "Localizar arquivo..." (sem perder tags/favoritos/campanhas)
  ou "Remover da biblioteca" (nunca apaga o arquivo do disco).
