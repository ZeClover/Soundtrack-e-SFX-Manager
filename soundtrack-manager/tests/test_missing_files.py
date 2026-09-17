"""Arquivos ausentes (item 48/etapa 3 item 11): relocalizar preserva tudo, remover não apaga o arquivo."""

from __future__ import annotations


def test_relocate_preserves_tags_favorite_campaigns_soundtrack_and_history(
    track_repo, tag_repo, campaign_repo, soundtrack_repo, history_repo, sample_track_id
):
    track_repo.set_favorite(sample_track_id, True)
    track_repo.set_note(sample_track_id, "nota importante")
    tag_repo.set_tags_for_track(sample_track_id, ["boss", "epico"])
    campaign_repo.set_campaigns_for_track(sample_track_id, ["Darkrem"])
    st = soundtrack_repo.create("Sessao 14")
    soundtrack_repo.add_track(st.id, sample_track_id)
    track_repo.register_play(sample_track_id)

    track_repo.mark_missing(1, seen_paths=set())  # simula o arquivo tendo sumido num scan
    assert track_repo.get_by_id(sample_track_id).is_missing is True

    track_repo.relocate(sample_track_id, "/novo/local/song.mp3", "song.mp3")

    track = track_repo.get_by_id(sample_track_id)
    assert track.is_missing is False
    assert track.absolute_path == "/novo/local/song.mp3"
    assert track.is_favorite is True
    assert track.note == "nota importante"
    assert track.tags == ["boss", "epico"]
    assert track.campaigns == ["Darkrem"]
    assert soundtrack_repo.has_track(st.id, sample_track_id) is True
    assert len(history_repo.recent_tracks()) == 1


def test_delete_removes_associations_but_never_touches_the_file_on_disk(
    tmp_path, track_repo, tag_repo, soundtrack_repo, library_root_repo
):
    real_file = tmp_path / "song.mp3"
    real_file.write_bytes(b"conteudo real")
    root_id = library_root_repo.get_or_create(str(tmp_path))
    track_id = track_repo.upsert_from_scan(
        library_root_id=root_id, absolute_path=str(real_file), relative_path="song.mp3",
        filename="song.mp3", extension=".mp3", title="Song", artist=None, album=None,
        duration_seconds=10, file_size=100, partial_hash="h", has_embedded_cover=False,
    )
    tag_repo.set_tags_for_track(track_id, ["boss"])
    st = soundtrack_repo.create("Sessao 14")
    soundtrack_repo.add_track(st.id, track_id)

    track_repo.delete(track_id)

    assert track_repo.get_by_id(track_id) is None
    assert soundtrack_repo.get_items(st.id) == []
    # O arquivo de verdade continua intacto no disco — remover da
    # biblioteca nunca apaga, move ou renomeia o arquivo original.
    assert real_file.exists()
    assert real_file.read_bytes() == b"conteudo real"
