from __future__ import annotations

from dataclasses import dataclass

from vistora.core import ModelCatalogView, ModelCardView, QualityPresetView, QualityTier


@dataclass(frozen=True)
class QualityPreset:
    tier: QualityTier
    detector_model: str
    restorer_model: str
    refiner_model: str | None
    notes: str


MODEL_CARDS: tuple[ModelCardView, ...] = (
    ModelCardView(
        id="yolo11x-seg-baseline",
        role="detector",
        family="YOLO segmentation",
        objective="balanced",
        maturity="baseline",
        notes="Stable baseline for segmentation-style mosaic detection.",
    ),
    ModelCardView(
        id="rtdetrv2-l-candidate",
        role="detector",
        family="RT-DETRv2",
        objective="quality-first",
        maturity="candidate",
        notes="Transformer detector candidate for stronger boundary quality.",
    ),
    ModelCardView(
        id="mask2former-swinl-candidate",
        role="detector",
        family="Mask2Former",
        objective="quality-first",
        maturity="candidate",
        notes="High-quality mask prediction candidate for hard scenes.",
    ),
    ModelCardView(
        id="basicvsrpp-v2-baseline",
        role="restorer",
        family="BasicVSR++",
        objective="balanced",
        maturity="baseline",
        notes="Baseline restoration backbone with good stability.",
    ),
    ModelCardView(
        id="rvrt-base-candidate",
        role="restorer",
        family="RVRT",
        objective="quality-first",
        maturity="candidate",
        notes="Video transformer candidate with improved temporal modeling.",
    ),
    ModelCardView(
        id="vrt-large-candidate",
        role="restorer",
        family="VRT",
        objective="quality-first",
        maturity="candidate",
        notes="High-capacity transformer candidate for best quality mode.",
    ),
    ModelCardView(
        id="swinir-video-refiner-candidate",
        role="refiner",
        family="SwinIR-style refiner",
        objective="quality-first",
        maturity="candidate",
        notes="Post-refinement pass to suppress ringing and texture artifacts.",
    ),
    ModelCardView(
        id="diffusion-video-refiner-candidate",
        role="refiner",
        family="Diffusion refiner",
        objective="quality-first",
        maturity="candidate",
        notes="Optional heavy refiner for highest perceptual quality setting.",
    ),
)

QUALITY_PRESETS: tuple[QualityPreset, ...] = (
    QualityPreset(
        tier="balanced",
        detector_model="yolo11x-seg-baseline",
        restorer_model="basicvsrpp-v2-baseline",
        refiner_model=None,
        notes="Default quality baseline with low risk.",
    ),
    QualityPreset(
        tier="high",
        detector_model="rtdetrv2-l-candidate",
        restorer_model="rvrt-base-candidate",
        refiner_model="swinir-video-refiner-candidate",
        notes="Quality-first recommended profile for most runs.",
    ),
    QualityPreset(
        tier="ultra",
        detector_model="mask2former-swinl-candidate",
        restorer_model="vrt-large-candidate",
        refiner_model="diffusion-video-refiner-candidate",
        notes="Maximum quality profile for best visual output.",
    ),
)


def build_model_catalog() -> ModelCatalogView:
    return ModelCatalogView(
        cards=list(MODEL_CARDS),
        quality_presets=[
            QualityPresetView(
                tier=p.tier,
                detector_model=p.detector_model,
                restorer_model=p.restorer_model,
                refiner_model=p.refiner_model,
                notes=p.notes,
            )
            for p in QUALITY_PRESETS
        ],
    )


def resolve_models(
    quality_tier: QualityTier,
    detector_model: str | None,
    restorer_model: str | None,
    refiner_model: str | None,
) -> tuple[str, str, str | None]:
    preset = next((p for p in QUALITY_PRESETS if p.tier == quality_tier), None)
    if preset is None:
        preset = QUALITY_PRESETS[1]
    resolved_detector = detector_model or preset.detector_model
    resolved_restorer = restorer_model or preset.restorer_model
    resolved_refiner = refiner_model if refiner_model is not None else preset.refiner_model
    return resolved_detector, resolved_restorer, resolved_refiner
