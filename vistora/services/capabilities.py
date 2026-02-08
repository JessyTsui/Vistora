from __future__ import annotations

from vistora.core import SystemCapabilityView


def detect_devices() -> list[str]:
    devices = ["cpu"]
    try:
        import torch

        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_properties(i).name
                devices.append(f"cuda:{i} ({name})")
        if hasattr(torch, "xpu") and torch.xpu.is_available():
            for i in range(torch.xpu.device_count()):
                name = torch.xpu.get_device_name(i)
                devices.append(f"xpu:{i} ({name})")
    except Exception:
        pass
    return devices


def build_capabilities() -> SystemCapabilityView:
    default_runner = "auto"
    return SystemCapabilityView(
        devices=detect_devices(),
        runners=["auto", "dry-run", "lada-cli"],
        quality_tiers=["balanced", "high", "ultra"],
        defaults={
            "runner": default_runner,
            "quality_tier": "ultra",
        },
    )
