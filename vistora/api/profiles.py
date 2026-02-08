from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from vistora.app.dependencies import get_profiles
from vistora.core import ProfileListView, ProfileUpdateRequest, ProfileView
from vistora.services.profiles import ProfileStore

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])


@router.get("", response_model=ProfileListView)
def list_profiles(profiles: ProfileStore = Depends(get_profiles)):
    return profiles.list_profiles()


@router.get("/{name}", response_model=ProfileView)
def get_profile(name: str, profiles: ProfileStore = Depends(get_profiles)):
    profile = profiles.get_profile(name)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile


@router.put("/{name}", response_model=ProfileView)
def put_profile(name: str, req: ProfileUpdateRequest, profiles: ProfileStore = Depends(get_profiles)):
    return profiles.put_profile(name, req.settings)
