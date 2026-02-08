# Benchmark Plan

## Goals

- Increase throughput while keeping restoration quality stable or better.
- Quantify both runtime metrics and visual fidelity.

## Datasets

- Internal set A: short clips with dense mosaics
- Internal set B: mixed scenes with sparse mosaics
- Internal set C: long-form videos for stability tests

## Runtime metrics

- FPS (end-to-end and per stage)
- GPU memory usage (mean / p95 / max)
- GPU utilization (mean / p95)
- CPU utilization and encode overhead

## Quality metrics

- PSNR
- SSIM
- LPIPS
- Optional subjective MOS on sampled clips

## Experiment matrix

- Batch strategy: fixed 4/8/16 vs adaptive
- Runner backend variants
- Clip length variants
- Encode preset variants

## Reporting

- Report mean, std, and 95% CI
- Include hardware + driver + dependency versions
- Publish command lines and seeds for reproducibility
