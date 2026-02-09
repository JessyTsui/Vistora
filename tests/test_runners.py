from __future__ import annotations

from unittest.mock import patch

from vistora.services.runners import DryRunRunner, LadaCliRunner, build_runner


def test_build_runner_auto_fallback_to_dry_run():
    with patch("vistora.services.runners.shutil.which", return_value=None):
        runner = build_runner("auto")
    assert isinstance(runner, DryRunRunner)


def test_build_runner_auto_prefers_lada_cli_when_available():
    with patch("vistora.services.runners.shutil.which", return_value="/usr/local/bin/lada-cli"):
        runner = build_runner("auto")
    assert isinstance(runner, LadaCliRunner)
