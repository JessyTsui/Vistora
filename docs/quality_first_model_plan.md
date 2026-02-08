# Quality-First Model Plan

## Objective

For this stage, quality is prioritized over speed:

1. improve detection mask quality
2. improve restoration fidelity and temporal consistency
3. use heavy refiner passes in high/ultra tiers

## Tier strategy

- `balanced`: stable baseline for broad usage
- `high`: default research/product recommendation
- `ultra`: maximum quality mode for premium jobs

## Model candidates in code

See `vistora/services/model_catalog.py`:

- Detector candidates:
  - `yolo11x-seg-baseline`
  - `rtdetrv2-l-candidate`
  - `mask2former-swinl-candidate`
- Restorer candidates:
  - `basicvsrpp-v2-baseline`
  - `rvrt-base-candidate`
  - `vrt-large-candidate`
- Refiner candidates:
  - `swinir-video-refiner-candidate`
  - `diffusion-video-refiner-candidate`

## Paper-oriented ablations

1. Detector swap (same restorer/refiner)
2. Restorer swap (same detector/refiner)
3. Refiner on/off
4. Tier comparison (`balanced` vs `high` vs `ultra`)

## Metrics

- Quality: PSNR, SSIM, LPIPS, temporal consistency score
- Runtime: FPS, latency, memory footprint

Current phase accepts runtime degradation if quality gain is significant and repeatable.
