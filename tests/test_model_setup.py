from __future__ import annotations

import hashlib
import json
from pathlib import Path

from vistora.services.model_setup import setup_models


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_setup_models_creates_template_when_manifest_missing(tmp_path: Path):
    manifest_path = tmp_path / "models" / "manifest.json"
    output_dir = tmp_path / "assets"

    result = setup_models(manifest_path=str(manifest_path), output_dir=str(output_dir))

    assert result.created_template is True
    assert result.total_models == 0
    assert manifest_path.exists()

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(payload.get("models"), list)


def test_setup_models_copies_local_file_and_skips_on_second_run(tmp_path: Path):
    source_file = tmp_path / "source.bin"
    data = b"vistora-model"
    source_file.write_bytes(data)

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "models": [
                    {
                        "id": "restorer.test",
                        "filename": "restorer.bin",
                        "path": str(source_file),
                        "sha256": _sha256(data),
                    }
                ],
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "models"
    first = setup_models(manifest_path=str(manifest_path), output_dir=str(output_dir))
    assert first.created_template is False
    assert first.failed == []
    assert first.downloaded == ["restorer.test"]

    target = output_dir / "restorer.bin"
    assert target.exists()
    assert target.read_bytes() == data

    second = setup_models(manifest_path=str(manifest_path), output_dir=str(output_dir))
    assert second.failed == []
    assert second.downloaded == []
    assert second.skipped == ["restorer.test"]
