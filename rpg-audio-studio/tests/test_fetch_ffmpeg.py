"""Regressão: o primeiro build Windows saiu sem FFmpeg porque
``ffmpeg.exe``/``ffprobe.exe`` nunca existiam antes do PyInstaller rodar
e o BUILD_WINDOWS.bat antigo só avisava e seguia em frente. Estes testes
cobrem a lógica pura de ``scripts/fetch_ffmpeg.py`` (checksum, extração,
localização dos binários, idempotência, falhas) sem depender de rede —
o download de verdade só é possível numa máquina Windows real.

Importado via inserção explícita de ``scripts/`` no ``sys.path`` e um
``import fetch_ffmpeg`` (nome próprio, não genérico) em vez de
``from scripts.fetch_ffmpeg import ...`` — o mesmo motivo da regressão de
``tests.*`` corrigida antes: ``scripts/`` também existe na raiz do
monorepo, então um import absoluto começando com ``scripts.`` correria o
mesmo risco de resolver para a pasta errada quando mais de um pytest do
monorepo roda no mesmo processo."""

from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import fetch_ffmpeg as ff


def _make_zip(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)


def _sha256_file(path: Path, dest: Path, label: str) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    dest.write_text(f"{digest} *{label}\n", encoding="utf-8")


@pytest.fixture
def isolated_ffmpeg_dir(tmp_path, monkeypatch):
    dest = tmp_path / "ffmpeg"
    monkeypatch.setattr(ff, "FFMPEG_DIR", dest)
    return dest


def test_verify_checksum_accepts_matching_hash(tmp_path):
    zip_path = tmp_path / "a.zip"
    zip_path.write_bytes(b"conteudo de teste")
    checksum_path = tmp_path / "a.zip.sha256"
    _sha256_file(zip_path, checksum_path, "a.zip")

    ff._verify_checksum(zip_path, checksum_path)  # não deve lançar


def test_verify_checksum_rejects_mismatched_hash(tmp_path):
    zip_path = tmp_path / "a.zip"
    zip_path.write_bytes(b"conteudo de teste")
    checksum_path = tmp_path / "a.zip.sha256"
    checksum_path.write_text("0" * 64 + " *a.zip\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Checksum SHA256"):
        ff._verify_checksum(zip_path, checksum_path)


def test_verify_checksum_rejects_file_without_a_valid_hash(tmp_path):
    zip_path = tmp_path / "a.zip"
    zip_path.write_bytes(b"conteudo de teste")
    checksum_path = tmp_path / "a.zip.sha256"
    checksum_path.write_text("nao e um hash valido", encoding="utf-8")

    with pytest.raises(RuntimeError, match="hash SHA256"):
        ff._verify_checksum(zip_path, checksum_path)


def test_extract_binaries_finds_them_inside_a_nested_bin_folder(tmp_path):
    """A build real do gyan.dev vem com os binários dentro de uma
    subpasta versionada, ex.: ffmpeg-7.1-essentials_build/bin/ — a busca
    precisa ser recursiva, não assumir um caminho fixo."""
    zip_path = tmp_path / "ffmpeg.zip"
    _make_zip(zip_path, {
        "ffmpeg-7.1-essentials_build/bin/ffmpeg.exe": b"fake ffmpeg",
        "ffmpeg-7.1-essentials_build/bin/ffprobe.exe": b"fake ffprobe",
        "ffmpeg-7.1-essentials_build/bin/ffplay.exe": b"fake ffplay (deve ser ignorado)",
        "ffmpeg-7.1-essentials_build/LICENSE.txt": b"GPLv3",
    })

    extract_dir = tmp_path / "extracted"
    found = ff._extract_binaries(zip_path, extract_dir)

    assert set(found) == {"ffmpeg.exe", "ffprobe.exe"}
    assert found["ffmpeg.exe"].read_bytes() == b"fake ffmpeg"
    assert found["ffprobe.exe"].read_bytes() == b"fake ffprobe"


def test_extract_binaries_raises_clearly_when_one_is_missing(tmp_path):
    zip_path = tmp_path / "incomplete.zip"
    _make_zip(zip_path, {"bin/ffmpeg.exe": b"fake ffmpeg"})

    with pytest.raises(RuntimeError, match="ffprobe.exe"):
        ff._extract_binaries(zip_path, tmp_path / "extracted")


def test_already_prepared_is_false_when_directory_is_empty(isolated_ffmpeg_dir):
    assert ff._already_prepared() is False


def test_already_prepared_is_true_only_when_both_binaries_validate(isolated_ffmpeg_dir, monkeypatch):
    isolated_ffmpeg_dir.mkdir(parents=True)
    (isolated_ffmpeg_dir / "ffmpeg.exe").write_bytes(b"x")
    (isolated_ffmpeg_dir / "ffprobe.exe").write_bytes(b"x")
    monkeypatch.setattr(ff, "_validate_binary", lambda path, name: True)

    assert ff._already_prepared() is True


def test_prepare_ffmpeg_skips_download_when_already_valid(isolated_ffmpeg_dir, monkeypatch):
    isolated_ffmpeg_dir.mkdir(parents=True)
    (isolated_ffmpeg_dir / "ffmpeg.exe").write_bytes(b"x")
    (isolated_ffmpeg_dir / "ffprobe.exe").write_bytes(b"x")
    monkeypatch.setattr(ff, "_validate_binary", lambda path, name: True)

    def _boom(*a, **k):
        raise AssertionError("nao deveria tentar baixar nada")

    monkeypatch.setattr(ff, "_download", _boom)

    ff.prepare_ffmpeg()  # não deve lançar nem tentar baixar


def test_prepare_ffmpeg_downloads_verifies_and_copies_binaries(isolated_ffmpeg_dir, monkeypatch, tmp_path):
    """Fluxo feliz completo, sem rede: ``_download`` é trocado por uma
    cópia de arquivos locais, o resto (checksum, extração, cópia,
    validação final) roda de verdade."""
    fixture_zip = tmp_path / "fixture.zip"
    _make_zip(fixture_zip, {
        "ffmpeg-x-essentials_build/bin/ffmpeg.exe": b"fake ffmpeg content",
        "ffmpeg-x-essentials_build/bin/ffprobe.exe": b"fake ffprobe content",
    })
    fixture_checksum = tmp_path / "fixture.zip.sha256"
    _sha256_file(fixture_zip, fixture_checksum, "ffmpeg-release-essentials.zip")

    def _fake_download(url, destination):
        source = fixture_zip if url == ff.DOWNLOAD_URL else fixture_checksum
        destination.write_bytes(source.read_bytes())

    monkeypatch.setattr(ff, "_download", _fake_download)
    monkeypatch.setattr(ff, "_validate_binary", lambda path, name: path.is_file())

    ff.prepare_ffmpeg()

    assert (isolated_ffmpeg_dir / "ffmpeg.exe").read_bytes() == b"fake ffmpeg content"
    assert (isolated_ffmpeg_dir / "ffprobe.exe").read_bytes() == b"fake ffprobe content"


def test_prepare_ffmpeg_raises_clearly_on_checksum_mismatch(isolated_ffmpeg_dir, monkeypatch, tmp_path):
    fixture_zip = tmp_path / "fixture.zip"
    _make_zip(fixture_zip, {
        "bin/ffmpeg.exe": b"fake ffmpeg",
        "bin/ffprobe.exe": b"fake ffprobe",
    })
    fixture_checksum = tmp_path / "fixture.zip.sha256"
    fixture_checksum.write_text("0" * 64 + " *ffmpeg-release-essentials.zip\n", encoding="utf-8")

    def _fake_download(url, destination):
        source = fixture_zip if url == ff.DOWNLOAD_URL else fixture_checksum
        destination.write_bytes(source.read_bytes())

    monkeypatch.setattr(ff, "_download", _fake_download)

    with pytest.raises(RuntimeError, match="Checksum SHA256"):
        ff.prepare_ffmpeg()

    # Nunca deve ter copiado nada pra pasta final com um download suspeito
    assert not (isolated_ffmpeg_dir / "ffmpeg.exe").exists()
