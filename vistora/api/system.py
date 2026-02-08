from __future__ import annotations

from fastapi import APIRouter

from vistora.core import ModelCatalogView, SystemCapabilityView
from vistora.services.capabilities import build_capabilities
from vistora.services.model_catalog import build_model_catalog

router = APIRouter(tags=["system"])


@router.get("/healthz")
def healthz():
    return {"ok": True}


@router.get("/api/v1/system/capabilities", response_model=SystemCapabilityView)
def capabilities():
    return build_capabilities()


@router.get("/api/v1/models/catalog", response_model=ModelCatalogView)
def models_catalog():
    return build_model_catalog()
