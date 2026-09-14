import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

from rpg_audio_shared.audio_meta import read_audio_metadata

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg não disponível neste ambiente")
def test_read_audio_metadata_from_tagged_mp3(tmp_path: Path):
    mp3_path = tmp_path / "track.mp3"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", "1", "-codec:a", "libmp3lame", "-b:a", "64k", str(mp3_path),
        ],
        check=True,
        capture_output=True,
    )

    audio = MP3(mp3_path)
    if audio.tags is None:
        audio.add_tags()
    audio.save()
    tags = EasyID3(mp3_path)
    tags["title"] = "Battle Against a True Hero"
    tags["artist"] = "Toby Fox"
    tags["album"] = "Undertale"
    tags.save()

    meta = read_audio_metadata(mp3_path)

    assert meta.title == "Battle Against a True Hero"
    assert meta.artist == "Toby Fox"
    assert meta.album == "Undertale"
    assert meta.duration_seconds == pytest.approx(1.0, abs=0.3)


def test_read_audio_metadata_falls_back_to_filename(tmp_path: Path):
    fake = tmp_path / "Untitled Track.mp3"
    fake.write_bytes(b"not really an mp3")

    meta = read_audio_metadata(fake)

    assert meta.title == "Untitled Track"
    assert meta.artist is None
    assert meta.duration_seconds == 0.0
