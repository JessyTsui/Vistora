from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8585
    runtime_dir: pathlib.Path = pathlib.Path("runtime")
    ledger_path: pathlib.Path = pathlib.Path("runtime/credits_ledger.json")
    profiles_path: pathlib.Path = pathlib.Path("runtime/profiles.json")
    enforce_credits: bool = False
    bootstrap_credit_user: str = "anonymous"
    bootstrap_credit_amount: int = 100


def load_settings() -> Settings:
    runtime_dir = pathlib.Path(os.getenv("VISTORA_RUNTIME_DIR", "runtime"))
    return Settings(
        host=os.getenv("VISTORA_HOST", "127.0.0.1"),
        port=int(os.getenv("VISTORA_PORT", "8585")),
        runtime_dir=runtime_dir,
        ledger_path=pathlib.Path(os.getenv("VISTORA_LEDGER_PATH", str(runtime_dir / "credits_ledger.json"))),
        profiles_path=pathlib.Path(os.getenv("VISTORA_PROFILES_PATH", str(runtime_dir / "profiles.json"))),
        enforce_credits=_as_bool(os.getenv("VISTORA_ENFORCE_CREDITS"), False),
        bootstrap_credit_user=os.getenv("VISTORA_BOOTSTRAP_CREDIT_USER", "anonymous"),
        bootstrap_credit_amount=max(0, int(os.getenv("VISTORA_BOOTSTRAP_CREDIT_AMOUNT", "100"))),
    )
