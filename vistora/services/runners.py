from __future__ import annotations

import re
import select
import shutil
import subprocess
import time
from typing import Protocol, Callable

from vistora.core import JobCreateRequest


StageCallback = Callable[[str, float], None]


class JobRunner(Protocol):
    def run(self, req: JobCreateRequest, on_stage: StageCallback) -> None:
        ...


class DryRunRunner:
    def run(self, req: JobCreateRequest, on_stage: StageCallback) -> None:
        if req.quality_tier == "ultra":
            stage_sleep = 0.9
        elif req.quality_tier == "high":
            stage_sleep = 0.7
        else:
            stage_sleep = 0.45
        sleep_override = req.options.get("stage_sleep")
        if isinstance(sleep_override, (int, float)):
            stage_sleep = max(0.0, float(sleep_override))

        stages = [
            ("probing", 0.05),
            ("decoding", 0.18),
            (f"detecting[{req.detector_model}]", 0.40),
            (f"restoring[{req.restorer_model}]", 0.78),
        ]
        if req.refiner_model:
            stages.append((f"refining[{req.refiner_model}]", 0.90))
        stages.extend(
            [
                ("encoding", 0.96),
                ("muxing", 1.0),
            ]
        )
        for stage, progress in stages:
            time.sleep(stage_sleep)
            on_stage(stage, progress)


class LadaCliRunner:
    def run(self, req: JobCreateRequest, on_stage: StageCallback) -> None:
        if req.output_path is None:
            raise ValueError("output_path is required for lada-cli runner")

        on_stage("probing", 0.05)
        command = [
            "lada-cli",
            "--input",
            req.input_path,
            "--output",
            req.output_path,
        ]

        if req.detector_model:
            command.extend(["--mosaic-detection-model", req.detector_model])
        if req.restorer_model:
            command.extend(["--mosaic-restoration-model", req.restorer_model])

        # Allow forwarding selected options as CLI args.
        for key, value in req.options.items():
            option_name = f"--{key.replace('_', '-')}"
            if isinstance(value, bool):
                if value:
                    command.append(option_name)
            else:
                command.extend([option_name, str(value)])

        on_stage("restoring", 0.3)
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        fd = proc.stdout.fileno()
        start = time.perf_counter()
        dynamic_progress = 0.3
        max_expected = max(8.0, float(req.duration_hint_seconds or 30) * 1.2)
        logs: list[str] = []

        while True:
            ready, _, _ = select.select([fd], [], [], 0.3)
            if ready:
                line = proc.stdout.readline()
                if line:
                    logs.append(line.rstrip("\n"))
                    match = re.search(r"(\d{1,3})\s*%", line)
                    if match:
                        pct = max(0.0, min(100.0, float(match.group(1))))
                        dynamic_progress = max(dynamic_progress, 0.3 + (pct / 100.0) * 0.65)
                        on_stage("restoring", min(dynamic_progress, 0.95))
            else:
                elapsed = time.perf_counter() - start
                guessed = min(0.93, 0.3 + (elapsed / max_expected) * 0.6)
                if guessed > dynamic_progress:
                    dynamic_progress = guessed
                    on_stage("restoring", dynamic_progress)

            if proc.poll() is not None:
                break

        remainder = proc.stdout.read()
        if remainder:
            logs.append(remainder.rstrip("\n"))
        exit_code = proc.wait()
        if exit_code != 0:
            stderr = "\n".join([line for line in logs if line]).strip() or "lada-cli execution failed"
            raise RuntimeError(stderr)
        on_stage("encoding", 0.97)
        on_stage("done", 1.0)


def build_runner(name: str) -> JobRunner:
    if name == "auto":
        return LadaCliRunner() if shutil.which("lada-cli") else DryRunRunner()
    if name == "dry-run":
        return DryRunRunner()
    if name == "lada-cli":
        return LadaCliRunner()
    raise ValueError(f"Unsupported runner: {name}")
