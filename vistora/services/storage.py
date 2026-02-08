from __future__ import annotations

import json
import pathlib
import threading
from typing import Any


class JsonStore:
    def __init__(self, path: pathlib.Path):
        self.path = path
        self._lock = threading.Lock()

    def load_dict(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return {}
            try:
                with self.path.open("r", encoding="utf-8") as f:
                    payload = json.load(f)
                return payload if isinstance(payload, dict) else {}
            except (OSError, json.JSONDecodeError):
                return {}

    def save_dict(self, payload: dict[str, Any]):
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=True, sort_keys=True)
            tmp.replace(self.path)
