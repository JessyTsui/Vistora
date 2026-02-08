from __future__ import annotations

from pathlib import Path

from vistora.services.pathing import default_output_path


def test_default_output_path_creates_output_dir(tmp_path: Path):
    output_dir = tmp_path / "my outputs"
    path = default_output_path(str(tmp_path / "sample clip.mp4"), output_dir=str(output_dir))

    generated = Path(path)
    assert output_dir.exists()
    assert generated.parent == output_dir
    assert generated.suffix == ".mp4"
    assert generated.name.startswith("sample_clip_restored_")
