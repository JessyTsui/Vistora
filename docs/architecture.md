# Vistora Architecture

## Layer Overview

1. `vistora/app/`
- Application bootstrap and dependency container.
- `container.py` builds runtime services from settings.
- `main.py` wires lifecycle hooks and route registration.

2. `vistora/api/`
- HTTP route layer only.
- Each domain has a dedicated router module:
  - `system.py`
  - `jobs.py`
  - `credits.py`
  - `profiles.py`
  - `telegram.py`
  - `web.py`

3. `vistora/services/`
- Business logic and stateful services.
- Examples:
  - `job_manager.py`: queue and worker lifecycle
  - `credits.py`: persistent credit ledger
  - `model_catalog.py`: quality-tier model selection
  - `runners.py`: backend runner abstraction

4. `vistora/core.py`
- Shared request/response and domain models (Pydantic).

## Request Flow

1. Request enters `api/*` router.
2. Router resolves service dependencies from `app.dependencies`.
3. Service layer executes business logic.
4. Router returns typed response models from `core.py`.

## Extension Points

1. Add a new inference backend:
- Implement in `vistora/services/runners.py`.
- Expose new runner id in `vistora/services/capabilities.py`.

2. Add a new API module:
- Create `vistora/api/<domain>.py`.
- Register in `vistora/api/router.py`.

3. Replace storage:
- Keep service interfaces stable.
- Swap `JsonStore` with DB-backed repositories.
