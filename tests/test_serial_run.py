from __future__ import annotations

from pathlib import Path

from vistora.services.serial_run import run_local_serial


def test_run_local_serial_uses_default_output_and_reports_progress(tmp_path: Path):
    input_path = tmp_path / "clip.mp4"
    input_path.write_text("dummy")

    events: list[tuple[str, float]] = []

    result = run_local_serial(
        input_path=str(input_path),
        runner="dry-run",
        quality_tier="balanced",
        output_dir=str(tmp_path / "outs"),
        options={"stage_sleep": 0},
        on_progress=lambda stage, progress, _elapsed, _fps, _eta: events.append((stage, progress)),
    )

    assert result.runner == "dry-run"
    assert result.output_path.startswith(str(tmp_path / "outs"))
    assert Path(result.output_path).exists()
    assert events
    assert events[-1][0] in {"muxing", "done"}
    assert events[-1][1] == 1.0
