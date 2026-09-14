# RPG Soundtrack Manager

Organiza uma biblioteca de músicas (de qualquer tamanho, sem duplicar arquivos)
em soundtracks para campanhas de RPG: favoritar, marcar tags, ouvir com um
player integrado e exportar a soundtrack final para uma pasta própria — sem
nunca mover, renomear ou apagar os arquivos originais.

Parte da suíte **RPG Audio Toolkit** (veja o [README da raiz](../README.md)).

## Status

MVP funcional (Etapa 2 do roadmap do projeto): biblioteca, scanner, busca,
favoritos, tags, soundtrack (criar/adicionar/reordenar/remover) com
salvamento automático, player integrado e exportação. Recursos avançados
(modo triagem, seções, histórico, campanhas na UI, detecção de duplicados)
ficam para uma etapa seguinte — o banco de dados já foi modelado para
suportá-los sem exigir migração.

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
repositórios do banco, exportação (numeração, conflitos, conversão) e a
navegação de playlist do player. Alguns testes que dependem do `ffmpeg`
são pulados automaticamente se ele não estiver disponível.

## Build (executável Windows)

Planejado para a Etapa 6 do projeto (PyInstaller, um `.exe` por app). Ainda
não implementado nesta fase.

## Estrutura

```text
soundtrack-manager/
    main.py                  # ponto de entrada (python main.py)
    app/
        config.py             # caminhos e constantes do app
        database/              # schema SQL + wrapper de conexão SQLite
        models/                 # dataclasses (Track, Soundtrack, Tag, Campaign...)
        repositories/            # acesso ao banco (uma classe por entidade)
        services/                # scanner (QThread), player, exportação
        ui/
            main_window.py        # orquestra os painéis e a lógica da app
            widgets/                # painéis: filtros, biblioteca, soundtrack, player
            dialogs/                # exportar, relatório de exportação, progresso do scan
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

Funcionam apenas quando o foco não está em um campo de texto.

| Tecla     | Ação                                  |
|-----------|----------------------------------------|
| `Espaço`  | Play / Pause                           |
| `Enter`   | Adicionar música selecionada à soundtrack |
| `F`       | Favoritar / desfavoritar               |
| `↑` / `↓` | Navegar pela lista da biblioteca        |
