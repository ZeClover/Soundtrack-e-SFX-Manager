"""Baixa e prepara o FFmpeg/FFprobe empacotados para o build Windows.

Correção pós-lançamento (nº 1): o primeiro build Windows saiu SEM FFmpeg
porque ninguém tinha colocado ``ffmpeg.exe``/``ffprobe.exe`` manualmente
em ``rpg-audio-studio/ffmpeg/`` antes de rodar o PyInstaller — o ``.spec``
só inclui o que já existir naquela pasta na hora do build, e o
``BUILD_WINDOWS.bat`` antigo só avisava e seguia em frente se estivesse
faltando. Isso passou a ser um passo automático e obrigatório do build.

Correção pós-lançamento (nº 2): a fonte original (gyan.dev) começou a
falhar com ``CERTIFICATE_VERIFY_FAILED: certificate has expired`` — a
verificação TLS continua ligada (é assim que ela pegou o problema), então
a fonte foi trocada para os releases do **BtbN/FFmpeg-Builds no GitHub**
(https://github.com/BtbN/FFmpeg-Builds/releases), que usa a infraestrutura
de certificados do próprio GitHub.

Fonte: build estático win64 GPL da tag "latest" do BtbN/FFmpeg-Builds —
uma das duas fontes recomendadas na própria página oficial de download do
FFmpeg (https://www.ffmpeg.org/download.html#build-windows, junto com o
gyan.dev). A tag "latest" é mantida pelo próprio BtbN como um ponteiro
estável e sempre atualizado (não uma versão fixa que "apodrece" com o
tempo, mas também não é scraping frágil — é uma URL de asset de release
do GitHub, previsível e documentada). Variante **estática** (não
"shared"), pra não precisar distribuir DLLs extras do FFmpeg junto do
``.exe``. Licenciado como **GPLv3** — ver ``THIRD_PARTY_LICENSES.md``.

Uso (chamado por BUILD_WINDOWS.bat, ou manualmente):
    python scripts/fetch_ffmpeg.py

Idempotente: se ``ffmpeg/ffmpeg.exe`` e ``ffmpeg/ffprobe.exe`` já
existirem e passarem na validação (rodar ``-version`` e conferir a
saída), não baixa de novo — permite builds repetidos sem depender de rede
toda vez, e respeita uma cópia colocada manualmente ali (ex.: uma build
LGPL escolhida deliberadamente em vez desta GPL).

Qualquer falha (rede, TLS, checksum não bate, zip com estrutura
inesperada, binário que não passa na validação) termina com um erro claro
e código de saída diferente de zero — nunca deixa passar silenciosamente
sem FFmpeg. A verificação de certificado TLS/SSL nunca é desligada aqui —
``urllib`` já verifica por padrão, e este script não mexe nisso.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from hashlib import sha256
from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parent.parent
FFMPEG_DIR = STUDIO_ROOT / "ffmpeg"

# Assets de release do GitHub redirecionam (302) pra uma URL assinada em
# release-assets.githubusercontent.com — urllib.request segue isso
# automaticamente (HTTPRedirectHandler já vem habilitado por padrão),
# sem precisar de nenhum tratamento especial além de mandar um
# User-Agent (alguns CDNs recusam requisições sem um).
RELEASE_BASE_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"
ASSET_FILENAME = "ffmpeg-master-latest-win64-gpl.zip"
DOWNLOAD_URL = f"{RELEASE_BASE_URL}/{ASSET_FILENAME}"
# Um arquivo de checksums só, cobrindo todos os assets da release (formato
# "sha256sum": "<hash>  <nome do arquivo>", uma linha por asset) — não um
# ".sha256" dedicado por arquivo como na fonte anterior.
CHECKSUMS_URL = f"{RELEASE_BASE_URL}/checksums.sha256"

USER_AGENT = "rpg-audio-studio-build-script"

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
    """A verificação de certificado TLS/SSL fica com o padrão do Python
    (ligada) — nada aqui passa um ``ssl.SSLContext`` alternativo nem
    desabilita a verificação."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def _find_checksum_for_asset(checksums_content: str, asset_filename: str) -> str:
    """O arquivo cobre todos os ~50 assets da release (Windows/Linux,
    x86_64/arm64, GPL/LGPL, estático/shared) — precisa achar a linha
    específica do nosso arquivo, não só pegar o primeiro hash que
    aparecer (que poderia ser de outro asset)."""
    for raw_line in checksums_content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        digest, name = parts
        name = name.strip().lstrip("*")
        if name != asset_filename:
            continue
        if len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            continue
        return digest.lower()

    raise RuntimeError(
        f"Não encontrei o checksum de '{asset_filename}' em checksums.sha256 — "
        "a lista de assets da release pode ter mudado."
    )


def _verify_checksum(zip_path: Path, checksums_path: Path, asset_filename: str) -> None:
    content = checksums_path.read_text(encoding="utf-8", errors="ignore")
    expected = _find_checksum_for_asset(content, asset_filename)

    actual = sha256(zip_path.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"Checksum SHA256 não bate para {asset_filename}: "
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
        zip_path = tmp_path / ASSET_FILENAME
        checksums_path = tmp_path / "checksums.sha256"

        _download(DOWNLOAD_URL, zip_path)
        _download(CHECKSUMS_URL, checksums_path)
        _verify_checksum(zip_path, checksums_path, ASSET_FILENAME)
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
