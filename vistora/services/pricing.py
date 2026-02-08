from __future__ import annotations

import math

from vistora.core import QualityTier


QUALITY_MULTIPLIER: dict[QualityTier, int] = {
    "balanced": 1,
    "high": 2,
    "ultra": 4,
}


def estimate_credits(duration_hint_seconds: int | None, quality_tier: QualityTier) -> int:
    duration = duration_hint_seconds if duration_hint_seconds and duration_hint_seconds > 0 else 120
    base = max(1, math.ceil(duration / 120))
    multiplier = QUALITY_MULTIPLIER[quality_tier]
    return base * multiplier
