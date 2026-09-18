from __future__ import annotations

import re

from app.version import APP_AUTHOR, APP_DESCRIPTION, APP_DISPLAY_NAME, APP_MODULES, APP_VERSION


def test_version_follows_semver_shape():
    assert re.match(r"^\d+\.\d+\.\d+$", APP_VERSION)


def test_display_metadata_is_non_empty():
    assert APP_DISPLAY_NAME == "RPG Audio Studio"
    assert APP_DESCRIPTION
    assert APP_AUTHOR


def test_modules_list_matches_the_three_integrated_modules():
    assert APP_MODULES == ("Soundtrack Manager", "SFX Manager", "Downloader")
