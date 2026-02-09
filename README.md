# Vistora

Quality-first video restoration workspace with:

- Local serial CLI (`vistora run`) with default best-quality presets
- FastAPI + Web console (`vistora serve`)
- Credit ledger, profiles, Telegram webhook simulation
- Model/benchmark/paper planning docs

## 60-Second Quick Start

Install `uv` first if needed: <https://docs.astral.sh/uv/getting-started/installation/>

```bash
cd ~/dev/vistora
uv sync --frozen --extra dev
```

## Fastest Path: Local CLI Run

```bash
uv run vistora run /path/to/input.mp4
```

Behavior:

- Serial execution (no worker/queue setup required)
- Default output auto-generated in `outputs/`
- Default runner `auto` (`lada-cli` if available, else `dry-run`)
- Default quality `ultra`
- Live progress includes stage, percent, FPS, ETA, elapsed time

Useful examples:

```bash
# explicit output file
uv run vistora run /path/to/input.mp4 --output /path/to/result.mp4

# only choose output directory
uv run vistora run /path/to/input.mp4 --output-dir ./outputs

# JSON output for scripts
uv run vistora run /path/to/input.mp4 --json
```

## Web UI / API Mode

Start service:

```bash
uv run vistora serve --host 127.0.0.1 --port 8585
```

Open:

- `http://127.0.0.1:8585`

The web form now defaults to `runner=auto`, `quality=ultra`, and output path can be left empty.

## API CLI (Optional)

If the service is running, you can still use API-style commands:

```bash
uv run vistora health
uv run vistora capabilities
uv run vistora models
uv run vistora jobs create --input /tmp/in.mp4 --user demo
uv run vistora jobs list
uv run vistora credits topup demo 50 --reason init
```

Default API base URL is `http://127.0.0.1:8585`.

```bash
export VISTORA_BASE_URL="http://127.0.0.1:8585"
```

## For AI Agents

```bash
cd ~/dev/vistora
uv sync --frozen --extra dev
uv run python -m py_compile $(rg --files -g '*.py' vistora tests)
uv run pytest -q
```

CLI smoke check:

```bash
echo "dummy" > /tmp/vistora_in.mp4
uv run vistora run /tmp/vistora_in.mp4 --runner dry-run --quality balanced --json
```

Main extension points:

- API routes: `vistora/api/`
- service logic: `vistora/services/`
- app composition: `vistora/app/container.py`, `vistora/app/main.py`
- web console: `vistora/web/`
- schemas: `vistora/core.py`

## Project Layout

```text
vistora/
  vistora/
    app/          # app bootstrap, settings, container
    api/          # domain routers
    services/     # job/credits/profile/runner logic
    web/          # static dashboard
    core.py       # request/response models
  tests/
  docs/
  scripts/
```

## Architecture Docs

- `docs/architecture.md`
- `docs/project_quality_first_master_plan.md`
- `docs/quality_first_model_plan.md`
- `docs/benchmark_plan.md`
- `docs/paper_track.md`

## GitHub PR Automation

Workflows in `.github/workflows/`:

- `ci.yml`: lockfile check + locked sync + compile/tests/CLI smoke/package build
- `pr-automation.yml`: sticky PR summary comment based on changed areas
- `dependency-review.yml`: dependency risk check on PR
- `.github/dependabot.yml`: weekly dependency and GitHub Actions update PRs

## Dependency Management Standard

- Source of truth: `pyproject.toml`
- Reproducible lockfile: `uv.lock` (committed)
- CI installs from lock: `uv sync --frozen --extra dev`
- Update lock after dependency changes:

```bash
uv lock
```

## Useful Scripts

```bash
./scripts/bootstrap.sh
./scripts/run_dev.sh
```
