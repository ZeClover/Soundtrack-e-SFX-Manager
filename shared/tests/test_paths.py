from pathlib import Path

from rpg_audio_shared.paths import numbered_filename, sanitize_filename, unique_path


def test_sanitize_removes_invalid_chars():
    assert sanitize_filename('Boss: Fight? "Final"') == "Boss_ Fight_ _Final_"


def test_sanitize_trims_spaces_and_dots():
    assert sanitize_filename("  Nome da Musica.  ") == "Nome da Musica"


def test_sanitize_handles_reserved_names():
    assert sanitize_filename("CON") == "_CON"
    assert sanitize_filename("com1") == "_com1"


def test_sanitize_empty_uses_fallback():
    assert sanitize_filename("   ") == "sem_titulo"
    assert sanitize_filename("..") == "sem_titulo"


def test_sanitize_replaces_invalid_chars_with_underscore():
    assert sanitize_filename("???") == "___"


def test_sanitize_keeps_accents_and_unicode():
    assert sanitize_filename("Dungeon Noturna - Ação") == "Dungeon Noturna - Ação"


def test_unique_path_appends_counter(tmp_path: Path):
    existing = tmp_path / "01 - Musica.mp3"
    existing.write_bytes(b"data")

    result = unique_path(existing)
    assert result == tmp_path / "01 - Musica (2).mp3"


def test_unique_path_skips_multiple_existing(tmp_path: Path):
    (tmp_path / "faixa.mp3").write_bytes(b"a")
    (tmp_path / "faixa (2).mp3").write_bytes(b"a")

    result = unique_path(tmp_path / "faixa.mp3")
    assert result == tmp_path / "faixa (3).mp3"


def test_unique_path_returns_same_when_free(tmp_path: Path):
    target = tmp_path / "livre.mp3"
    assert unique_path(target) == target


def test_numbered_filename():
    assert numbered_filename(1, "Battle Theme", ".mp3") == "01 - Battle Theme.mp3"
    assert numbered_filename(12, "Boss", ".flac") == "12 - Boss.flac"
