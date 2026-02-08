from __future__ import annotations

import argparse
import pathlib
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from vistora.api import register_routes
from vistora.app.container import AppContainer, build_container
from vistora.app.settings import Settings, load_settings


def create_app(settings: Settings | None = None, container: AppContainer | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    resolved_container = container or build_container(resolved_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        resolved_container.jobs.start()
        try:
            yield
        finally:
            resolved_container.jobs.stop()

    app = FastAPI(title="Vistora API", version="0.1.0", lifespan=lifespan)
    app.state.container = resolved_container
    # Backward-compatible state aliases for callers that still access direct handles.
    app.state.ledger = resolved_container.ledger
    app.state.profiles = resolved_container.profiles
    app.state.jobs = resolved_container.jobs
    app.state.tg_ops = resolved_container.tg_ops

    web_dir = pathlib.Path(__file__).parents[1] / "web"
    app.mount("/web", StaticFiles(directory=str(web_dir)), name="web")

    register_routes(app, web_dir=web_dir)

    return app


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Vistora web service")
    parser.add_argument("--host", default=None, help="Bind host. Defaults to VISTORA_HOST or 127.0.0.1")
    parser.add_argument("--port", type=int, default=None, help="Bind port. Defaults to VISTORA_PORT or 8585")
    parser.add_argument("--reload", action="store_true")
    return parser


def main():
    args = _build_arg_parser().parse_args()
    settings = load_settings()
    host = args.host or settings.host
    port = args.port or settings.port
    uvicorn.run(create_app(), host=host, port=port, reload=args.reload, log_level="info")


if __name__ == "__main__":
    main()
