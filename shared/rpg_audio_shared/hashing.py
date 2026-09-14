"""Identificação de arquivos sem depender apenas do caminho absoluto.

Para bibliotecas com milhares de arquivos, calcular um hash completo de cada
arquivo a cada escaneamento seria lento. Em vez disso usamos um "hash
parcial" barato (tamanho + amostras do início/fim do arquivo) que é rápido
o suficiente para rodar em toda a biblioteca e ainda assim serve como boa
impressão digital para reconhecer arquivos movidos/renomeados.

Um hash completo (SHA-256 do conteúdo inteiro) fica disponível para quando
for necessária uma confirmação mais forte, por exemplo na detecção de
duplicados.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_SAMPLE_SIZE = 65536  # 64 KiB do início e do fim do arquivo


def partial_hash(path: Path) -> str:
    """Hash rápido baseado no tamanho do arquivo e amostras de início/fim.

    Não lê o arquivo inteiro, então tem custo praticamente constante mesmo
    para arquivos grandes (FLAC de dezenas de MB).
    """
    size = path.stat().st_size
    digest = hashlib.sha256()
    digest.update(str(size).encode("utf-8"))

    with path.open("rb") as fh:
        digest.update(fh.read(_SAMPLE_SIZE))
        if size > _SAMPLE_SIZE:
            fh.seek(max(size - _SAMPLE_SIZE, 0))
            digest.update(fh.read(_SAMPLE_SIZE))

    return digest.hexdigest()


def full_hash(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Hash SHA-256 completo do conteúdo do arquivo (uso sob demanda)."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()
