"""Baixa e prepara o FFmpeg/FFprobe empacotados para o build Windows.

Correção pós-lançamento: o primeiro build Windows saiu SEM FFmpeg porque
ninguém tinha colocado ``ffmpeg.exe``/``ffprobe.exe`` manualmente em
``rpg-audio-studio/ffmpeg/`` antes de rodar o PyInstaller — o ``.spec`` só
inclui o que já existir naquela pasta na hora do build, e o
``BUILD_WINDOWS.bat`` antigo só avisava e seguia em frente se estivesse
faltando. Isso passa a ser um passo automático e obrigatório do build.

Fonte: build "release essentials" do FFmpeg para Windows, mantido por
Gyan Doshi (gyan.dev) — uma das duas fontes recomendadas na própria
página oficial de download do FFmpeg
(https://www.ffmpeg.org/download.html#build-windows, junto com o BtbN).
Licenciado como GPLv3 pelo próprio gyan.dev (arquivo LICENSE.txt incluído
no zip, copiado do repositório do FFmpeg) — ver ``THIRD_PARTY_LICENSES.md``.

Uso (chamado por BUILD_WINDOWS.bat, ou manualmente):
    python scripts/fetch_ffmpeg.py

Idempotente: se ``ffmpeg/ffmpeg.exe`` e ``ffmpeg/ffprobe.exe`` já
existirem e passarem na validação (rodar ``-version`` e conferir a
saída), não baixa de novo — permite builds repetidos sem depender de rede
toda vez, e respeita uma cópia colocada manualmente ali (ex.: uma build
LGPL escolhida deliberadamente em vez desta GPL).

Qualquer falha (rede, checksum não bate, zip com estrutura inesperada,
binário que não passa na validação) termina com um erro claro e código de
saída diferente de zero — nunca deixa passar silenciosamente sem FFmpeg.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parent.parent
FFMPEG_DIR = STUDIO_ROOT / "ffmpeg"

DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
CHECKSUM_URL = DOWNLOAD_URL + ".sha256"

BINARY_NAMES = ("ffmpeg.exe", "ffprobe.exe")


def _validate_binary(path: Path, expected_name: str) -> bool:
    """Roda ``<binário> -version`` e confere que a saída realmente parece
    a daquele programa (equivalente ao pedido de validar com algo
    parecido com ``ffmpeg -version``)."""
    if not path.is_file():
        return False
    try:
        result = subprocess.run(
            [str(path), "-version"], capture_output=True, text=True, timeout=15,
        )
    except OSError:
        return False
    if result.returncode != 0:
        return False
    return f"{expected_name} version" in result.stdout.lower()


def _already_prepared() -> bool:
    return all(
        _validate_binary(FFMPEG_DIR / name, name.removesuffix(".exe"))
        for name in BINARY_NAMES
    )


def _download(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def _verify_checksum(zip_path: Path, checksum_path: Path) -> None:
    content = checksum_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"[0-9a-fA-F]{64}", content)
    if not match:
        raise RuntimeError(f"Não encontrei um hash SHA256 válido em {checksum_path.name}")
    expected = match.group(0).lower()

    actual = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"Checksum SHA256 não bate para {zip_path.name}: "
            f"esperado {expected}, obtido {actual}. Download corrompido ou adulterado."
        )


def _extract_binaries(zip_path: Path, extract_dir: Path) -> dict[str, Path]:
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)

    found: dict[str, Path] = {}
    for name in BINARY_NAMES:
        matches = list(extract_dir.rglob(name))
        if not matches:
            raise RuntimeError(
                f"Não encontrei '{name}' dentro do zip baixado — a estrutura do "
                "build do FFmpeg pode ter mudado."
            )
        found[name] = matches[0]
    return found


def prepare_ffmpeg() -> None:
    if _already_prepared():
        print(f"FFmpeg já preparado em {FFMPEG_DIR} (validado com -version) — pulando download.")
        return

    print(f"Baixando FFmpeg de: {DOWNLOAD_URL}")
    FFMPEG_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="rpg-audio-studio-ffmpeg-") as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "ffmpeg-release-essentials.zip"
        checksum_path = tmp_path / "ffmpeg-release-essentials.zip.sha256"

        _download(DOWNLOAD_URL, zip_path)
        _download(CHECKSUM_URL, checksum_path)
        _verify_checksum(zip_path, checksum_path)
        print("Checksum SHA256 confirmado.")

        extract_dir = tmp_path / "extracted"
        binaries = _extract_binaries(zip_path, extract_dir)

        for name, source in binaries.items():
            shutil.copy2(source, FFMPEG_DIR / name)

    if not _already_prepared():
        raise RuntimeError(
            "FFmpeg foi baixado e extraído, mas ffmpeg.exe/ffprobe.exe não "
            "passaram na validação (-version) depois de copiados."
        )

    print(f"FFmpeg preparado com sucesso em {FFMPEG_DIR}")


if __name__ == "__main__":
    try:
        prepare_ffmpeg()
    except Exception as exc:  # noqa: BLE001 - qualquer falha aqui precisa parar o build, não só logar
        print(f"[ERRO] Falha ao preparar o FFmpeg empacotado: {exc}", file=sys.stderr)
        sys.exit(1)
