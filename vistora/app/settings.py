from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8585
    runtime_dir: pathlib.Path = pathlib.Path("runtime")
    ledger_path: pathlib.Path = pathlib.Path("runtime/credits_ledger.json")
    profiles_path: pathlib.Path = pathlib.Path("runtime/profiles.json")


def load_settings() -> Settings:
    runtime_dir = pathlib.Path(os.getenv("VISTORA_RUNTIME_DIR", "runtime"))
    return Settings(
        host=os.getenv("VISTORA_HOST", "127.0.0.1"),
        port=int(os.getenv("VISTORA_PORT", "8585")),
        runtime_dir=runtime_dir,
        ledger_path=pathlib.Path(os.getenv("VISTORA_LEDGER_PATH", str(runtime_dir / "credits_ledger.json"))),
        profiles_path=pathlib.Path(os.getenv("VISTORA_PROFILES_PATH", str(runtime_dir / "profiles.json"))),
    )
