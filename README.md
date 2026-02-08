# Vistora

Quality-first video restoration workspace with:

- FastAPI service
- Web console
- CLI client
- job queue + credits + profiles
- benchmark and paper-oriented planning docs

## 60-Second Quick Start

```bash
cd ~/dev/vistora
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
vistora-web --host 127.0.0.1 --port 8585
```

Open: `http://127.0.0.1:8585`

## CLI Quick Start

In another terminal:

```bash
cd ~/dev/vistora
source .venv/bin/activate
vistora-cli health
vistora-cli jobs create --input /tmp/in.mp4 --output /tmp/out.mp4 --user demo --quality high
vistora-cli jobs list
vistora-cli credits topup demo 50 --reason init
```

Default API base URL is `http://127.0.0.1:8585`.
Override with:

```bash
export VISTORA_BASE_URL="http://127.0.0.1:8585"
```

## For AI Agents

If you are an AI coding agent, use this minimum loop:

```bash
cd ~/dev/vistora
source .venv/bin/activate
pip install -e ".[dev]"
python -m py_compile $(rg --files -g '*.py' vistora tests)
pytest -q
```

Main extension points:

- API routes: `vistora/api/`
- service logic: `vistora/services/`
- app composition: `vistora/app/container.py`, `vistora/app/main.py`
- web console: `vistora/web/`
- schemas: `vistora/core.py`

## Run Modes

1. Web + API

```bash
vistora-web --host 127.0.0.1 --port 8585 --reload
```

2. CLI against running API

```bash
vistora-cli capabilities
vistora-cli models
```

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

- `ci.yml`: compile + tests + package build (PR and main push)
- `pr-automation.yml`: sticky PR summary comment based on changed areas
- `dependency-review.yml`: dependency risk check on PR

## Useful Scripts

```bash
./scripts/bootstrap.sh
./scripts/run_dev.sh
```
