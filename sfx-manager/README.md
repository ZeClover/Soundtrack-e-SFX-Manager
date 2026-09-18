# RPG SFX Manager

Organiza uma biblioteca de efeitos sonoros (de qualquer tamanho, sem duplicar
arquivos) em categorias e packs para campanhas de RPG: tocar rapidamente
(inclusive vários efeitos ao mesmo tempo), favoritar, marcar tags, atribuir
teclas de atalho e exportar um pack para uma pasta própria — sem nunca mover,
renomear ou apagar os arquivos originais.

Parte da suíte **RPG Audio Toolkit** (veja o [README da raiz](../README.md)).
Tem UX própria: cor de destaque diferente, biblioteca em grade de cards
(com alternância para lista), categorias por pasta em vez de sections,
reprodução simultânea de vários efeitos e um sistema de hotkeys de uma
tecla só. Desde a Etapa 5, este módulo é embutido como a página "SFX e
Packs" do **RPG Audio Studio** (`../rpg-audio-studio/`), que é o app que o
usuário final abre — mas continua rodando sozinho normalmente com
`python main.py`, útil para desenvolvimento/depuração isolada.

## Status

Etapa 4 do roadmap do projeto concluída: biblioteca com escaneamento
automático (categoria detectada pela subpasta), busca, favoritos, tags,
observações, visualização em cards ou lista, reprodução rápida (com suporte
a tocar vários efeitos ao mesmo tempo ou só um por vez), teclas de atalho de
efeito único, packs de SFX (criar/adicionar/reordenar/remover/exportar),
detector de duplicados e tratamento de arquivos ausentes.

## COMO TESTAR NO WINDOWS

Forma mais simples, sem usar linha de comando:

1. Baixe/clone o repositório inteiro (a pasta `shared/` ao lado de
   `sfx-manager/` é necessária — não copie só esta pasta).
2. Abra a pasta `sfx-manager`.
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
`FFmpeg` é opcional — só é necessário se você usar "Converter" ao exportar
um pack para um formato diferente do original; sem ele, o resto do programa
funciona normalmente (o `ABRIR.bat`/`INSTALAR.bat` avisam se ele não for
encontrado).

Se algo der errado: apague a pasta `.venv` (dentro de `sfx-manager`) e rode
`INSTALAR.bat` novamente.

## Instalação (desenvolvimento)

Requer Python 3.10+ e [FFmpeg](https://ffmpeg.org/download.html) instalado e
disponível no PATH (usado apenas para converter formato na exportação — a
reprodução e o escaneamento não precisam dele).

```bash
# a partir da raiz do repositório
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r sfx-manager/requirements.txt
```

O `requirements.txt` já instala o pacote `shared/` (`rpg_audio_shared`) em
modo editável — não é preciso instalar nada manualmente ali.

## Executar em desenvolvimento

```bash
cd sfx-manager
python main.py
```

## Testes

```bash
cd sfx-manager
pytest
```

Os testes rodam em modo *headless* (`QT_QPA_PLATFORM=offscreen`, configurado
automaticamente em `tests/conftest.py`) e cobrem: escaneamento de biblioteca
com detecção automática de categoria pela subpasta, repositórios do banco
(efeitos, tags, packs, hotkeys — incluindo um teste de regressão específico
para o id do item do pack nunca ser confundido com o id do efeito),
reprodução simultânea vs. modo de voz única do player, exportação (formato,
conflitos, conversão), detector de duplicados e os modelos/painel usados
pela biblioteca (cards e lista). Alguns testes que dependem do `ffmpeg` são
pulados automaticamente se ele não estiver disponível.

## Build (executável Windows)

Planejado para a Etapa 6 do projeto (PyInstaller, um `.exe` por app). Ainda
não implementado nesta fase.

## Estrutura

```text
sfx-manager/
    ABRIR.bat                # Windows: instala (1a vez) e abre o programa
    INSTALAR.bat              # Windows: instala/reinstala as dependências
    main.py                  # ponto de entrada (python main.py)
    app/
        config.py             # caminhos, categorias sugeridas, teclas de atalho permitidas
        database/              # schema SQL + wrapper de conexão SQLite
        models/                 # dataclasses (SfxTrack, SfxPack, Category, Tag...)
        repositories/            # acesso ao banco (uma classe por entidade)
        services/                # scanner (QThread), player (multi-voz), exportação, duplicados
        ui/
            main_window.py        # orquestra os painéis e a lógica da app
            widgets/                # painéis: filtros/categorias, biblioteca (cards/lista), packs
            dialogs/                # categorias, hotkey, exportar, duplicados, progresso do scan
    tests/                    # pytest (banco, scanner, player, exportação, modelos de UI)
```

`shared/rpg_audio_shared` (na raiz do monorepo) concentra o que é comum aos
três apps da suíte: sanitização de caminhos, hashing, leitura de metadados
de áudio, tema escuro Qt e utilitários de formatação.

## Banco de dados

SQLite local em `%APPDATA%\RPG Audio Toolkit\sfx-manager\sfx_manager.db` no
Windows (em outros sistemas, usado apenas em desenvolvimento, cai em
`~/.rpg-audio-toolkit/sfx-manager/`). Principais tabelas: `sfx_tracks`,
`sfx_categories`, `sfx_tags` / `sfx_track_tags`, `sfx_packs` /
`sfx_pack_items`, `sfx_hotkeys`, `sfx_play_history`, `settings`,
`library_roots`.

A biblioteca **nunca** copia, move ou renomeia os arquivos de áudio
originais — o banco apenas guarda metadados e classificações (favorito,
tags, categoria, observação) apontando para o caminho original. Um rescan
detecta arquivos novos e marca como "ausente" (sem apagar do banco) os que
sumiram, sem reprocessar metadados de arquivos já conhecidos. A categoria de
cada efeito é detectada automaticamente pela subpasta imediata dentro da
pasta da biblioteca (ex.: `Biblioteca/Portas/porta_madeira.wav` vira
categoria "Portas") e pode ser trocada manualmente depois.

## Configurações

A pasta da biblioteca selecionada é lembrada automaticamente (tabela
`settings`) e recarregada na próxima abertura do programa.

## Atalhos de teclado

Na janela principal, funcionam apenas quando o foco não está em um campo de texto.

| Tecla                    | Ação                                          |
|---------------------------|-------------------------------------------------|
| Teclas atribuídas (`1`–`0`, `A`–`Z`) | Tocar o efeito associado àquela tecla (ver "Hotkeys" abaixo) |

## Recursos

- **Categorias automáticas**: ao escanear, a subpasta imediata de cada
  arquivo vira sua categoria; gerencie/renomeie categorias em "Gerenciar
  categorias..." no painel de filtros.
- **Cards ou lista**: botão de alternância no topo da biblioteca troca entre
  uma grade de cards (com ícone por categoria, duração, estrela de favorito
  e emblema de hotkey) e uma tabela compacta — ambas usam model/view do Qt,
  então continuam responsivas com milhares de efeitos.
- **Reprodução rápida e simultânea**: clique/duplo-clique num card toca o
  efeito na hora; por padrão vários efeitos podem tocar ao mesmo tempo
  (útil para camadas de ambiente + impacto), com uma opção para restringir a
  um efeito por vez (interrompe o anterior). Botão "🔇 Parar tudo" na barra
  inferior encerra toda reprodução ativa.
- **Hotkeys de uma tecla**: clique com o botão direito num efeito → "Atribuir
  tecla" escolhe uma tecla simples (dígito ou letra, sem modificadores) que,
  pressionada em qualquer lugar da janela (fora de campos de texto), toca
  aquele efeito imediatamente; o diálogo avisa se a tecla já está em uso por
  outro efeito.
- **Packs de SFX**: crie packs temáticos (ex.: "Combate — Sala do Chefe"),
  adicione efeitos, reordene e exporte o pack inteiro (mantendo o formato
  original ou convertendo) para uma pasta própria.
- **Detector de duplicados**: botão "Localizar duplicados" na barra de
  ferramentas. Nunca remove nada sozinho — mostra os grupos (confirmado por
  hash, ou possível por nome/tamanho/duração) para você decidir.
- **Arquivos ausentes**: clique com o botão direito num efeito marcado como
  ausente para "Localizar arquivo..." (sem perder tags/favorito/hotkey) ou
  "Remover da biblioteca" (nunca apaga o arquivo do disco).
