from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from vistora.core import JobCreateRequest, QualityTier
from vistora.services.model_catalog import resolve_models
from vistora.services.pathing import default_output_path
from vistora.services.runners import DryRunRunner, LadaCliRunner, build_runner

ProgressCallback = Callable[[str, float, float, float | None, float | None], None]


@dataclass(frozen=True)
class VideoProbe:
    duration_seconds: float | None
    fps: float | None
    total_frames: int | None


@dataclass(frozen=True)
class LocalRunResult:
    input_path: str
    output_path: str
    runner: str
    quality_tier: QualityTier
    detector_model: str
    restorer_model: str
    refiner_model: str | None
    duration_hint_seconds: int
    elapsed_seconds: float
    avg_fps: float | None
    total_frames: int | None


def _parse_rate(raw: str | None) -> float | None:
    if not raw:
        return None
    if "/" in raw:
        left, right = raw.split("/", 1)
        try:
            denom = float(right)
            if denom == 0:
                return None
            return float(left) / denom
        except ValueError:
            return None
    try:
        return float(raw)
    except ValueError:
        return None


def probe_video(input_path: str) -> VideoProbe:
    if shutil.which("ffprobe") is None:
        return VideoProbe(duration_seconds=None, fps=None, total_frames=None)
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=avg_frame_rate,nb_frames,duration",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        input_path,
    ]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return VideoProbe(duration_seconds=None, fps=None, total_frames=None)
    if proc.returncode != 0:
        return VideoProbe(duration_seconds=None, fps=None, total_frames=None)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return VideoProbe(duration_seconds=None, fps=None, total_frames=None)
    stream = (payload.get("streams") or [{}])[0]
    fps = _parse_rate(stream.get("avg_frame_rate"))
    duration = None
    try:
        duration = float(stream.get("duration") or payload.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        duration = None
    frames = None
    raw_frames = stream.get("nb_frames")
    if raw_frames not in (None, "N/A"):
        try:
            frames = int(raw_frames)
        except ValueError:
            frames = None
    if frames is None and duration is not None and fps is not None and fps > 0:
        frames = max(1, int(duration * fps))
    return VideoProbe(duration_seconds=duration, fps=fps, total_frames=frames)


def _resolve_output_path(input_path: str, output_path: str | None, output_dir: str) -> str:
    if not output_path:
        return default_output_path(input_path=input_path, output_dir=output_dir)
    requested = Path(output_path)
    if output_path.endswith("/") or (requested.exists() and requested.is_dir()):
        requested.mkdir(parents=True, exist_ok=True)
        return default_output_path(input_path=input_path, output_dir=str(requested))
    requested.parent.mkdir(parents=True, exist_ok=True)
    return str(requested)


def _runner_name_from_instance(runner: object) -> str:
    if isinstance(runner, LadaCliRunner):
        return "lada-cli"
    if isinstance(runner, DryRunRunner):
        return "dry-run"
    return type(runner).__name__


def run_local_serial(
    input_path: str,
    output_path: str | None = None,
    output_dir: str = "outputs",
    runner: str = "auto",
    quality_tier: QualityTier = "ultra",
    detector_model: str | None = None,
    restorer_model: str | None = None,
    refiner_model: str | None = None,
    duration_hint_seconds: int | None = None,
    options: dict[str, str | int | float | bool] | None = None,
    on_progress: ProgressCallback | None = None,
) -> LocalRunResult:
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"input_path not found: {input_path}")

    resolved_detector, resolved_restorer, resolved_refiner = resolve_models(
        quality_tier,
        detector_model,
        restorer_model,
        refiner_model,
    )
    probe = probe_video(input_path)
    hint_seconds = duration_hint_seconds or int(probe.duration_seconds or 0) or 120
    resolved_output = _resolve_output_path(input_path=input_path, output_path=output_path, output_dir=output_dir)

    req = JobCreateRequest(
        input_path=input_path,
        output_path=resolved_output,
        user_id="local",
        runner=runner,  # type: ignore[arg-type]
        quality_tier=quality_tier,
        detector_model=resolved_detector,
        restorer_model=resolved_restorer,
        refiner_model=resolved_refiner,
        duration_hint_seconds=hint_seconds,
        options=options or {},
    )

    runner_impl = build_runner(req.runner)
    start = time.perf_counter()

    def _handle_stage(stage: str, progress: float):
        if on_progress is None:
            return
        safe_progress = max(0.0, min(1.0, progress))
        elapsed = max(0.001, time.perf_counter() - start)
        fps = None
        if probe.total_frames and safe_progress > 0:
            processed_frames = probe.total_frames * safe_progress
            fps = processed_frames / elapsed
        eta = None
        if safe_progress > 0:
            eta = elapsed * (1.0 - safe_progress) / safe_progress
        on_progress(stage, safe_progress, elapsed, fps, eta)

    runner_impl.run(req, on_stage=_handle_stage)

    if isinstance(runner_impl, DryRunRunner) and not Path(resolved_output).exists():
        if source.is_file():
            shutil.copy2(source, resolved_output)
        else:
            Path(resolved_output).touch()

    elapsed_total = time.perf_counter() - start
    avg_fps = None
    if probe.total_frames:
        avg_fps = probe.total_frames / max(0.001, elapsed_total)

    return LocalRunResult(
        input_path=input_path,
        output_path=resolved_output,
        runner=_runner_name_from_instance(runner_impl),
        quality_tier=quality_tier,
        detector_model=resolved_detector,
        restorer_model=resolved_restorer,
        refiner_model=resolved_refiner,
        duration_hint_seconds=hint_seconds,
        elapsed_seconds=elapsed_total,
        avg_fps=avg_fps,
        total_frames=probe.total_frames,
    )
