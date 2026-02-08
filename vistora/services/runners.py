from __future__ import annotations

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
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode != 0:
            stderr = process.stderr.strip() or process.stdout.strip() or "lada-cli execution failed"
            raise RuntimeError(stderr)
        on_stage("done", 1.0)


def build_runner(name: str) -> JobRunner:
    if name == "dry-run":
        return DryRunRunner()
    if name == "lada-cli":
        return LadaCliRunner()
    raise ValueError(f"Unsupported runner: {name}")
