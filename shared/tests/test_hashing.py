from pathlib import Path

from rpg_audio_shared.hashing import full_hash, partial_hash


def test_partial_hash_stable_for_same_content(tmp_path: Path):
    file_a = tmp_path / "a.mp3"
    file_b = tmp_path / "b.mp3"
    content = b"fake-audio-bytes" * 100
    file_a.write_bytes(content)
    file_b.write_bytes(content)

    assert partial_hash(file_a) == partial_hash(file_b)


def test_partial_hash_differs_for_different_content(tmp_path: Path):
    file_a = tmp_path / "a.mp3"
    file_b = tmp_path / "b.mp3"
    file_a.write_bytes(b"content-one" * 50)
    file_b.write_bytes(b"content-two" * 50)

    assert partial_hash(file_a) != partial_hash(file_b)


def test_partial_hash_handles_small_files(tmp_path: Path):
    tiny = tmp_path / "tiny.wav"
    tiny.write_bytes(b"x")
    assert partial_hash(tiny)  # não deve lançar exceção


def test_full_hash_differs_from_partial_hash(tmp_path: Path):
    f = tmp_path / "song.mp3"
    f.write_bytes(b"0123456789" * 10000)
    assert full_hash(f) != partial_hash(f)


def test_full_hash_deterministic(tmp_path: Path):
    f = tmp_path / "song.mp3"
    f.write_bytes(b"abc" * 1000)
    assert full_hash(f) == full_hash(f)
