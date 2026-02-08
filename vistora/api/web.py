from __future__ import annotations

import pathlib

from fastapi import APIRouter
from fastapi.responses import FileResponse


def build_web_router(web_dir: pathlib.Path) -> APIRouter:
    router = APIRouter(include_in_schema=False)

    @router.get("/")
    def index():
        return FileResponse(web_dir / "index.html")

    return router
