# rpg_audio_shared

Componentes reutilizáveis pelos três apps da suíte **RPG Audio Toolkit**
(veja o [README da raiz](../README.md)). Não é um aplicativo — é uma
biblioteca instalada em modo editável por cada app (`pip install -e ../shared`,
já incluído nos `requirements.txt`).

## Conteúdo

- `paths.py` — sanitização de nomes de arquivo/pasta para Windows, caminhos únicos.
- `hashing.py` — identificação de arquivos (hash parcial rápido + hash completo sob demanda).
- `audio_meta.py` — leitura de metadados de áudio (mutagen) com fallback seguro.
- `formats.py` — extensões de áudio suportadas.
- `formatting.py` — formatação de duração/tamanho de arquivo para a UI.
- `theme.py` — tema escuro Qt compartilhado (paleta + QSS).
- `app_dirs.py` / `logging_setup.py` — diretórios de dados/log por app e configuração de logging.

## Testes

```bash
cd shared
pip install -e .
pytest
```
