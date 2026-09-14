from rpg_audio_shared.formatting import format_duration, format_file_size


def test_format_duration_minutes_seconds():
    assert format_duration(151) == "2:31"
    assert format_duration(0) == "0:00"
    assert format_duration(59) == "0:59"


def test_format_duration_hours():
    assert format_duration(3725) == "1:02:05"


def test_format_file_size():
    assert format_file_size(500) == "500 B"
    assert format_file_size(2048) == "2.0 KB"
    assert format_file_size(1_500_000_000) == "1.4 GB"
