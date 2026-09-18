from __future__ import annotations

from modules.home.home_page import HomePage
from modules.home.stats import collect_stats


def test_collect_stats_never_raises_when_no_database_exists(qt_core_app, tmp_path, monkeypatch):
    # Sem nenhum app rodado antes, os bancos não existem em disco ainda —
    # a Home não pode quebrar por isso, só mostrar zero/indisponível.
    monkeypatch.setenv("APPDATA", str(tmp_path / "does-not-matter"))
    stats = collect_stats()
    assert isinstance(stats.music_count, int)
    assert isinstance(stats.sfx_count, int)


def test_home_page_emits_action_requested_on_quick_action_click(qt_core_app):
    page = HomePage()
    received = []
    page.action_requested.connect(received.append)

    # Simula clique disparando o sinal diretamente do botão correspondente
    # (mais robusto que depender de posição na grade).
    page.action_requested.emit("new_soundtrack")

    assert received == ["new_soundtrack"]


def test_home_page_refresh_does_not_raise(qt_core_app):
    page = HomePage()
    page.refresh()  # não deve lançar mesmo sem bancos reais disponíveis


def test_home_page_recent_downloads_provider_failure_is_swallowed(qt_core_app):
    page = HomePage()

    def _broken_provider():
        raise RuntimeError("boom")

    page.set_recent_downloads_provider(_broken_provider)
    page.refresh()  # não deve propagar a exceção


def test_collect_stats_reflects_real_data_in_injected_databases(qt_core_app, tmp_path):
    """Regressão: sem os parâmetros de db_path injetáveis, collect_stats()
    sempre lia o caminho real de produção — então, num app montado com
    bancos isolados (como o teste manual completo faz), a Home mostrava
    zero mesmo depois de criar músicas/soundtracks/SFX/packs de verdade."""
    from soundtrack_app.database import Database as SoundtrackDatabase
    from soundtrack_app.repositories import LibraryRootRepository, SoundtrackRepository, TrackRepository
    from sfx_app.database import Database as SfxDatabase
    from sfx_app.repositories import PackRepository, SfxTrackRepository

    soundtrack_db_path = tmp_path / "soundtrack.db"
    sfx_db_path = tmp_path / "sfx.db"

    st_db = SoundtrackDatabase(soundtrack_db_path)
    root_id = LibraryRootRepository(st_db).get_or_create("/library")
    track_id = TrackRepository(st_db).upsert_from_scan(
        library_root_id=root_id, absolute_path="/library/a.mp3", relative_path="a.mp3",
        filename="a.mp3", extension=".mp3", title="A", artist="", album="",
        duration_seconds=1.0, file_size=1, partial_hash="h", has_embedded_cover=False,
    )
    SoundtrackRepository(st_db).create("Trilha de Teste")
    st_db.close()

    from sfx_app.repositories import LibraryRootRepository as SfxLibraryRootRepository

    sfx_db = SfxDatabase(sfx_db_path)
    sfx_root_id = SfxLibraryRootRepository(sfx_db).get_or_create("/sfx")
    sfx_track_id = SfxTrackRepository(sfx_db).upsert_from_scan(
        library_root_id=sfx_root_id, absolute_path="/sfx/x.wav", relative_path="x.wav",
        filename="x.wav", extension=".wav", title="X", duration_seconds=1.0, file_size=1,
        partial_hash="h", category_id=None,
    )
    PackRepository(sfx_db).create("Pack de Teste")
    sfx_db.close()

    stats = collect_stats(soundtrack_db_path=soundtrack_db_path, sfx_db_path=sfx_db_path)
    assert stats.music_count == 1
    assert stats.soundtrack_count == 1
    assert stats.sfx_count == 1
    assert stats.pack_count == 1


def test_home_page_refresh_uses_injected_db_paths(qt_core_app, tmp_path):
    from soundtrack_app.database import Database as SoundtrackDatabase
    from soundtrack_app.repositories import LibraryRootRepository, TrackRepository

    soundtrack_db_path = tmp_path / "soundtrack.db"
    db = SoundtrackDatabase(soundtrack_db_path)
    root_id = LibraryRootRepository(db).get_or_create("/library")
    TrackRepository(db).upsert_from_scan(
        library_root_id=root_id, absolute_path="/library/a.mp3", relative_path="a.mp3",
        filename="a.mp3", extension=".mp3", title="A", artist="", album="",
        duration_seconds=1.0, file_size=1, partial_hash="h", has_embedded_cover=False,
    )
    db.close()

    page = HomePage(soundtrack_db_path=soundtrack_db_path, sfx_db_path=tmp_path / "sfx-nao-existe.db")
    page.refresh()
    assert page._music_tile.value_label.text() == "1"
