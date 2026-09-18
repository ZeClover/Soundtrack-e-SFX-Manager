"""Regressões: o primeiro build Windows saiu sem FFmpeg porque
``ffmpeg.exe``/``ffprobe.exe`` nunca existiam antes do PyInstaller rodar,
e o BUILD_WINDOWS.bat antigo só avisava e seguia em frente. Depois, a
fonte original (gyan.dev) passou a falhar com um certificado TLS
expirado, então a fonte foi trocada para os releases do
BtbN/FFmpeg-Builds no GitHub. Estes testes cobrem a lógica pura de
``scripts/fetch_ffmpeg.py`` (checksum — inclusive escolher a linha certa
num arquivo com dezenas de assets —, extração, localização dos binários,
idempotência, falhas) sem depender de rede — o download de verdade só é
possível numa máquina Windows real.

Importado via inserção explícita de ``scripts/`` no ``sys.path`` e um
``import fetch_ffmpeg`` (nome próprio, não genérico) em vez de
``from scripts.fetch_ffmpeg import ...`` — o mesmo motivo da regressão de
``tests.*`` corrigida antes: ``scripts/`` também existe na raiz do
monorepo, então um import absoluto começando com ``scripts.`` correria o
mesmo risco de resolver para a pasta errada quando mais de um pytest do
monorepo roda no mesmo processo."""

from __future__ import annotations

import sys
import zipfile
from hashlib import sha256
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


def _checksums_line(path: Path, filename: str) -> str:
    digest = sha256(path.read_bytes()).hexdigest()
    return f"{digest}  {filename}\n"


def _write_combined_checksums(dest: Path, *lines: str) -> None:
    dest.write_text("".join(lines), encoding="utf-8")


@pytest.fixture
def isolated_ffmpeg_dir(tmp_path, monkeypatch):
    dest = tmp_path / "ffmpeg"
    monkeypatch.setattr(ff, "FFMPEG_DIR", dest)
    return dest


def test_find_checksum_for_asset_picks_the_matching_line_among_many():
    """checksums.sha256 do BtbN cobre ~50 assets (Windows/Linux,
    x86_64/arm64, GPL/LGPL, estático/shared) — a busca precisa achar a
    linha do nosso arquivo específico, não a primeira que aparecer."""
    content = (
        "aaaa000000000000000000000000000000000000000000000000000000000001  ffmpeg-master-latest-linux64-gpl.tar.xz\n"
        "aaaa000000000000000000000000000000000000000000000000000000000002  ffmpeg-master-latest-win64-lgpl.zip\n"
        "aaaa000000000000000000000000000000000000000000000000000000000003  ffmpeg-master-latest-win64-gpl.zip\n"
        "aaaa000000000000000000000000000000000000000000000000000000000004  ffmpeg-master-latest-winarm64-gpl.zip\n"
    )

    found = ff._find_checksum_for_asset(content, "ffmpeg-master-latest-win64-gpl.zip")

    assert found == "aaaa000000000000000000000000000000000000000000000000000000000003"


def test_find_checksum_for_asset_raises_clearly_when_filename_absent():
    content = "aaaa000000000000000000000000000000000000000000000000000000000001  outro-arquivo.zip\n"

    with pytest.raises(RuntimeError, match="ffmpeg-master-latest-win64-gpl.zip"):
        ff._find_checksum_for_asset(content, "ffmpeg-master-latest-win64-gpl.zip")


def test_verify_checksum_accepts_matching_hash(tmp_path):
    zip_path = tmp_path / ff.ASSET_FILENAME
    zip_path.write_bytes(b"conteudo de teste")
    checksums_path = tmp_path / "checksums.sha256"
    _write_combined_checksums(
        checksums_path,
        "aaaa000000000000000000000000000000000000000000000000000000000abc  outro-asset.zip\n",
        _checksums_line(zip_path, ff.ASSET_FILENAME),
    )

    ff._verify_checksum(zip_path, checksums_path, ff.ASSET_FILENAME)  # não deve lançar


def test_verify_checksum_rejects_mismatched_hash(tmp_path):
    zip_path = tmp_path / ff.ASSET_FILENAME
    zip_path.write_bytes(b"conteudo de teste")
    checksums_path = tmp_path / "checksums.sha256"
    _write_combined_checksums(checksums_path, "0" * 64 + f"  {ff.ASSET_FILENAME}\n")

    with pytest.raises(RuntimeError, match="Checksum SHA256"):
        ff._verify_checksum(zip_path, checksums_path, ff.ASSET_FILENAME)


def test_verify_checksum_rejects_file_without_a_matching_entry(tmp_path):
    zip_path = tmp_path / ff.ASSET_FILENAME
    zip_path.write_bytes(b"conteudo de teste")
    checksums_path = tmp_path / "checksums.sha256"
    checksums_path.write_text("isto nao e um arquivo de checksums valido", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Não encontrei o checksum"):
        ff._verify_checksum(zip_path, checksums_path, ff.ASSET_FILENAME)


def test_extract_binaries_finds_them_inside_a_nested_bin_folder(tmp_path):
    """A build real do BtbN vem com os binários dentro de uma subpasta
    versionada, ex.: ffmpeg-master-latest-win64-gpl/bin/ — a busca
    precisa ser recursiva, não assumir um caminho fixo."""
    zip_path = tmp_path / "ffmpeg.zip"
    _make_zip(zip_path, {
        "ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe": b"fake ffmpeg",
        "ffmpeg-master-latest-win64-gpl/bin/ffprobe.exe": b"fake ffprobe",
        "ffmpeg-master-latest-win64-gpl/bin/ffplay.exe": b"fake ffplay (deve ser ignorado)",
        "ffmpeg-master-latest-win64-gpl/LICENSE.txt": b"GPLv3",
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
    cópia de arquivos locais, o resto (checksum contra um arquivo
    combinado com vários assets, extração, cópia, validação final) roda
    de verdade."""
    fixture_zip = tmp_path / "fixture.zip"
    _make_zip(fixture_zip, {
        "ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe": b"fake ffmpeg content",
        "ffmpeg-master-latest-win64-gpl/bin/ffprobe.exe": b"fake ffprobe content",
    })
    fixture_checksums = tmp_path / "checksums.sha256"
    _write_combined_checksums(
        fixture_checksums,
        "bbbb000000000000000000000000000000000000000000000000000000000001  ffmpeg-master-latest-linux64-gpl.tar.xz\n",
        _checksums_line(fixture_zip, ff.ASSET_FILENAME),
    )

    def _fake_download(url, destination):
        source = fixture_zip if url == ff.DOWNLOAD_URL else fixture_checksums
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
    fixture_checksums = tmp_path / "checksums.sha256"
    _write_combined_checksums(fixture_checksums, "0" * 64 + f"  {ff.ASSET_FILENAME}\n")

    def _fake_download(url, destination):
        source = fixture_zip if url == ff.DOWNLOAD_URL else fixture_checksums
        destination.write_bytes(source.read_bytes())

    monkeypatch.setattr(ff, "_download", _fake_download)

    with pytest.raises(RuntimeError, match="Checksum SHA256"):
        ff.prepare_ffmpeg()

    # Nunca deve ter copiado nada pra pasta final com um download suspeito
    assert not (isolated_ffmpeg_dir / "ffmpeg.exe").exists()


def test_download_never_disables_tls_verification():
    """Regressão específica do pedido: TLS/SSL nunca pode ser desligado
    aqui — nem um ssl.SSLContext alternativo, nem
    ssl._create_unverified_context, nem um parâmetro "verify=False" (que
    nem existe em urllib, mas garantindo que ninguém troque a
    implementação por requests com isso amanhã). Verifica o CÓDIGO da
    função, não o texto do docstring (que legitimamente fala sobre
    TLS/SSL para explicar essa garantia)."""
    import inspect

    source = inspect.getsource(ff._download)
    body = source.split('"""', 2)[-1] if '"""' in source else source

    for forbidden in ("_create_unverified_context", "CERT_NONE", "verify=False", "check_hostname"):
        assert forbidden not in body, f"'{forbidden}' encontrado no código de _download"
