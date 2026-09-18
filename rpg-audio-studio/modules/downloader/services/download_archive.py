"""Registro simples (um ID de vídeo por linha) de itens já baixados — usado
para nunca baixar a mesma música duas vezes entre sessões diferentes do
Downloader (item 31: "download archive")."""

from __future__ import annotations

from pathlib import Path


class DownloadArchive:
    def __init__(self, path: Path):
        self._path = Path(path)

    def contains(self, video_id: str) -> bool:
        if not video_id or not self._path.exists():
            return False
        return video_id in self._path.read_text(encoding="utf-8").splitlines()

    def add(self, video_id: str) -> None:
        if not video_id:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(video_id + "\n")
