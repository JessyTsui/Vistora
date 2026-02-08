from __future__ import annotations

import pathlib

from fastapi import FastAPI

from vistora.api.credits import router as credits_router
from vistora.api.jobs import router as jobs_router
from vistora.api.profiles import router as profiles_router
from vistora.api.system import router as system_router
from vistora.api.telegram import router as telegram_router
from vistora.api.web import build_web_router


def register_routes(app: FastAPI, web_dir: pathlib.Path) -> None:
    app.include_router(build_web_router(web_dir))
    app.include_router(system_router)
    app.include_router(jobs_router)
    app.include_router(credits_router)
    app.include_router(profiles_router)
    app.include_router(telegram_router)
