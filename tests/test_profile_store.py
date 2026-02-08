from __future__ import annotations

import pathlib

from vistora.services.profiles import ProfileStore
from vistora.services.storage import JsonStore


def test_put_and_get_profile(tmp_path: pathlib.Path):
    store = ProfileStore(JsonStore(tmp_path / "profiles.json"))
    store.put_profile("hq-fast", {"fp16": True, "max_clip_length": 180})
    profile = store.get_profile("hq-fast")
    assert profile is not None
    assert profile.settings["fp16"] is True

    listed = store.list_profiles()
    assert len(listed.profiles) == 1
    assert listed.profiles[0].name == "hq-fast"
