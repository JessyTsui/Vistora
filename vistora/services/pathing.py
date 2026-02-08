from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path


def default_output_path(input_path: str, output_dir: str = "outputs") -> str:
    src = Path(input_path)
    stem = src.stem if src.stem else "result"
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    safe_stem = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in stem).strip("_") or "result"
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir / f"{safe_stem}_restored_{stamp}.mp4")
