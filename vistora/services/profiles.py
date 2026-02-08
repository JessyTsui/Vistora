from __future__ import annotations

from vistora.core import ProfileListView, ProfileView
from vistora.services.storage import JsonStore


class ProfileStore:
    def __init__(self, store: JsonStore):
        self._store = store
        payload = self._store.load_dict()
        self._profiles: dict[str, dict] = payload.get("profiles", {}) if isinstance(payload.get("profiles"), dict) else {}

    def list_profiles(self) -> ProfileListView:
        profiles = [ProfileView(name=name, settings=settings) for name, settings in sorted(self._profiles.items(), key=lambda kv: kv[0])]
        return ProfileListView(profiles=profiles)

    def get_profile(self, name: str) -> ProfileView | None:
        settings = self._profiles.get(name)
        if settings is None:
            return None
        return ProfileView(name=name, settings=settings)

    def put_profile(self, name: str, settings: dict):
        self._profiles[name] = settings
        self._store.save_dict({"profiles": self._profiles})
        return ProfileView(name=name, settings=settings)
