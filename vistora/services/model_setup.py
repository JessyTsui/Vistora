from __future__ import annotations

import hashlib
import json
import shutil
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_TEMPLATE: dict[str, Any] = {
    "version": 1,
    "notes": [
        "Replace URL/path fields with your real model sources.",
        "sha256 is optional but recommended for integrity verification.",
    ],
    "models": [
        {
            "id": "detector.mask2former_swinl",
            "filename": "mask2former_swinl.pt",
            "url": "https://example.com/models/mask2former_swinl.pt",
            "sha256": "",
            "description": "Quality-first detector for hard boundaries.",
        },
        {
            "id": "restorer.vrt_large",
            "filename": "vrt_large.pth",
            "url": "https://example.com/models/vrt_large.pth",
            "sha256": "",
            "description": "Quality-first restoration backbone.",
        },
        {
            "id": "refiner.diffusion_video",
            "filename": "diffusion_video_refiner.safetensors",
            "url": "https://example.com/models/diffusion_video_refiner.safetensors",
            "sha256": "",
            "description": "Optional heavy refiner for best perceptual quality.",
        },
    ],
}


@dataclass(frozen=True)
class ManifestModel:
    id: str
    filename: str
    url: str | None = None
    local_path: str | None = None
    sha256: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class ModelSetupResult:
    manifest_path: str
    output_dir: str
    created_template: bool
    total_models: int
    downloaded: list[str]
    skipped: list[str]
    failed: list[dict[str, str]]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_sha(raw: Any, field: str) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip().lower()
    if not value:
        return None
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"invalid {field}: must be 64-char hex sha256")
    return value


def _infer_filename(model_id: str, url: str | None, local_path: str | None) -> str:
    if local_path:
        name = Path(local_path).name
        if name:
            return name
    if url:
        parsed = urllib.parse.urlparse(url)
        name = Path(parsed.path).name
        if name:
            return name
    return f"{model_id}.bin"


def _parse_entry(raw: Any, idx: int) -> ManifestModel:
    if not isinstance(raw, dict):
        raise ValueError(f"models[{idx}] must be an object")

    model_id = str(raw.get("id") or "").strip()
    if not model_id:
        raise ValueError(f"models[{idx}].id is required")

    url_raw = raw.get("url")
    local_raw = raw.get("path")
    url = str(url_raw).strip() if url_raw is not None else ""
    local_path = str(local_raw).strip() if local_raw is not None else ""
    if not url and not local_path:
        raise ValueError(f"models[{idx}] requires either 'url' or 'path'")

    filename_raw = str(raw.get("filename") or "").strip()
    filename = Path(filename_raw).name if filename_raw else _infer_filename(model_id, url or None, local_path or None)
    if not filename:
        raise ValueError(f"models[{idx}].filename cannot be empty")

    sha = _normalize_sha(raw.get("sha256"), f"models[{idx}].sha256")
    description_raw = raw.get("description")
    description = str(description_raw).strip() if description_raw is not None else None

    return ManifestModel(
        id=model_id,
        filename=filename,
        url=url or None,
        local_path=local_path or None,
        sha256=sha,
        description=description or None,
    )


def write_manifest_template(manifest_path: str) -> None:
    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    example_path = Path("models/manifest.example.json")
    if example_path.exists():
        path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
        return
    path.write_text(json.dumps(DEFAULT_TEMPLATE, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def load_manifest(manifest_path: str) -> list[ManifestModel]:
    path = Path(manifest_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    models_raw = payload.get("models")
    if not isinstance(models_raw, list):
        raise ValueError("manifest.models must be a JSON array")
    return [_parse_entry(item, idx) for idx, item in enumerate(models_raw)]


def _download_url(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "vistora-model-setup/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def _fetch_to_tmp(model: ManifestModel, tmp_path: Path) -> None:
    if model.local_path:
        src = Path(model.local_path)
        if not src.exists() or not src.is_file():
            raise RuntimeError(f"source path not found: {src}")
        shutil.copy2(src, tmp_path)
        return
    assert model.url is not None
    _download_url(model.url, tmp_path)


def setup_models(
    manifest_path: str = "models/manifest.json",
    output_dir: str = "models/assets",
    force: bool = False,
    dry_run: bool = False,
) -> ModelSetupResult:
    manifest = Path(manifest_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not manifest.exists():
        write_manifest_template(str(manifest))
        return ModelSetupResult(
            manifest_path=str(manifest),
            output_dir=str(out_dir),
            created_template=True,
            total_models=0,
            downloaded=[],
            skipped=[],
            failed=[],
        )

    models = load_manifest(str(manifest))
    downloaded: list[str] = []
    skipped: list[str] = []
    failed: list[dict[str, str]] = []

    for model in models:
        target = out_dir / model.filename
        if target.exists() and not force:
            if model.sha256:
                current_sha = _sha256_file(target)
                if current_sha != model.sha256:
                    failed.append(
                        {
                            "id": model.id,
                            "reason": (
                                f"existing file hash mismatch at {target}; rerun with --force "
                                "to re-download"
                            ),
                        }
                    )
                    continue
            skipped.append(model.id)
            continue

        if dry_run:
            downloaded.append(model.id)
            continue

        tmp_path = target.with_suffix(target.suffix + ".tmp")
        if tmp_path.exists():
            tmp_path.unlink()

        try:
            _fetch_to_tmp(model, tmp_path)
            if model.sha256:
                actual = _sha256_file(tmp_path)
                if actual != model.sha256:
                    raise RuntimeError(
                        f"sha256 mismatch for {model.id}: expected {model.sha256}, got {actual}"
                    )
            tmp_path.replace(target)
            downloaded.append(model.id)
        except Exception as exc:
            failed.append({"id": model.id, "reason": str(exc)})
            if tmp_path.exists():
                tmp_path.unlink()

    return ModelSetupResult(
        manifest_path=str(manifest),
        output_dir=str(out_dir),
        created_template=False,
        total_models=len(models),
        downloaded=downloaded,
        skipped=skipped,
        failed=failed,
    )
