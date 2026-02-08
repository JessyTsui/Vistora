# Vistora Roadmap

## Phase 0 (current)

- [x] Clean repo scaffold
- [x] API + web console
- [x] Queue + credits + profiles
- [x] Telegram webhook integration points

## Phase 1: performance baseline

- [ ] Build deterministic benchmark set (480p/1080p/4K)
- [ ] Add stage-level tracing (decode/detect/restore/encode)
- [ ] Implement adaptive detection batch policy by VRAM telemetry
- [ ] Compare against reference pipeline on same hardware

## Phase 2: quality + throughput

- [ ] Integrate optimized detector backend (TensorRT/ONNX Runtime optional)
- [ ] Explore decode acceleration backend and async transfer
- [ ] Add temporal consistency checks and artifact score
- [ ] Add auto profile recommendation by hardware

## Phase 3: productization

- [ ] User auth and quota tiers
- [ ] Payment provider integration for topup
- [ ] Telegram bot command workflow
- [ ] Order delivery and callback system

## Phase 4: paper-ready experiments

- [ ] Finalize benchmark protocol
- [ ] Run ablations for throughput/quality tradeoff
- [ ] Report confidence intervals and significance tests
- [ ] Produce short workshop-style paper draft
