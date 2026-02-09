from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from vistora.services.model_setup import ModelSetupResult, setup_models
from vistora.services.serial_run import LocalRunResult, run_local_serial

DEFAULT_BASE_URL = os.getenv("VISTORA_BASE_URL", "http://127.0.0.1:8585")


def _join_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def _parse_json_object(raw: str, field_name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return value


def _request(base_url: str, method: str, path: str, timeout: float, payload: dict[str, Any] | None = None) -> Any:
    url = _join_url(base_url, path)
    headers = {"Accept": "application/json"}
    body: bytes | None = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    req = urllib.request.Request(url=url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if not raw:
                return {"ok": True}
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return json.loads(raw.decode("utf-8"))
            return {"text": raw.decode("utf-8")}
    except urllib.error.HTTPError as exc:
        detail = exc.reason
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            if isinstance(payload, dict):
                detail = payload.get("detail") or payload
            else:
                detail = payload
        except Exception:
            pass
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"request failed: {exc.reason}") from exc


def _print(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _fmt_seconds(seconds: float | None) -> str:
    if seconds is None:
        return "--:--"
    value = max(0, int(seconds))
    minutes, sec = divmod(value, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def _coerce_option_value(raw: str) -> str | int | float | bool:
    lowered = raw.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    candidate = raw.strip()
    if candidate and all(ch in "+-0123456789" for ch in candidate):
        try:
            return int(candidate)
        except ValueError:
            pass
    try:
        return float(candidate)
    except ValueError:
        return raw


def _parse_options(option_items: list[str], options_json: str) -> dict[str, str | int | float | bool]:
    options: dict[str, str | int | float | bool] = {}
    if options_json.strip():
        parsed = _parse_json_object(options_json, "options-json")
        for key, value in parsed.items():
            if isinstance(value, (bool, int, float, str)):
                options[str(key)] = value
            else:
                raise ValueError(f"options-json only supports primitive values, got {key}={type(value).__name__}")
    for item in option_items:
        if "=" not in item:
            raise ValueError(f"invalid --option '{item}', expected KEY=VALUE")
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"invalid --option '{item}', key is empty")
        options[key] = _coerce_option_value(raw_value.strip())
    return options


def _local_result_to_dict(result: LocalRunResult) -> dict[str, Any]:
    return {
        "input_path": result.input_path,
        "output_path": result.output_path,
        "runner": result.runner,
        "quality_tier": result.quality_tier,
        "detector_model": result.detector_model,
        "restorer_model": result.restorer_model,
        "refiner_model": result.refiner_model,
        "duration_hint_seconds": result.duration_hint_seconds,
        "elapsed_seconds": round(result.elapsed_seconds, 3),
        "avg_fps": round(result.avg_fps, 3) if result.avg_fps is not None else None,
        "total_frames": result.total_frames,
    }


def _setup_result_to_dict(result: ModelSetupResult) -> dict[str, Any]:
    return {
        "manifest_path": result.manifest_path,
        "output_dir": result.output_dir,
        "created_template": result.created_template,
        "total_models": result.total_models,
        "downloaded": result.downloaded,
        "skipped": result.skipped,
        "failed": result.failed,
    }


def _print_local_human(result: LocalRunResult) -> None:
    print("Run complete")
    print(f"  input:   {result.input_path}")
    print(f"  output:  {result.output_path}")
    print(f"  runner:  {result.runner}")
    print(f"  quality: {result.quality_tier}")
    print(f"  models:  {result.detector_model} | {result.restorer_model} | {result.refiner_model or '-'}")
    print(f"  elapsed: {_fmt_seconds(result.elapsed_seconds)} ({result.elapsed_seconds:.2f}s)")
    if result.avg_fps is not None:
        print(f"  avg fps: {result.avg_fps:.2f}")
    if result.total_frames is not None:
        print(f"  frames:  {result.total_frames}")


def _print_setup_human(result: ModelSetupResult) -> None:
    if result.created_template:
        print(f"Manifest template created: {result.manifest_path}")
        print("Edit URL/path/sha256 entries and rerun `vistora setup-models`.")
        return

    print("Model setup complete")
    print(f"  manifest:   {result.manifest_path}")
    print(f"  output dir: {result.output_dir}")
    print(f"  total:      {result.total_models}")
    print(f"  downloaded: {len(result.downloaded)}")
    if result.downloaded:
        print(f"    ids:      {', '.join(result.downloaded)}")
    print(f"  skipped:    {len(result.skipped)}")
    if result.skipped:
        print(f"    ids:      {', '.join(result.skipped)}")
    print(f"  failed:     {len(result.failed)}")
    if result.failed:
        for item in result.failed:
            print(f"    - {item.get('id', 'unknown')}: {item.get('reason', 'unknown error')}")


def _cmd_run(args: argparse.Namespace) -> None:
    options = _parse_options(args.option or [], args.options_json)
    state = {
        "last_emit": 0.0,
        "last_stage": "",
        "last_progress": -1.0,
        "line_len": 0,
    }

    def _on_progress(stage: str, progress: float, elapsed: float, fps: float | None, eta: float | None) -> None:
        now = time.monotonic()
        should_emit = now - state["last_emit"] >= args.progress_interval
        if stage != state["last_stage"]:
            should_emit = True
        if abs(progress - state["last_progress"]) >= 0.005:
            should_emit = True
        if progress >= 1.0:
            should_emit = True
        if not should_emit:
            return

        pct = int(round(max(0.0, min(1.0, progress)) * 100))
        fps_text = f"{fps:.2f}" if fps is not None else "--"
        stage_text = stage if len(stage) <= 26 else f"{stage[:25]}+"
        line = (
            f"[{stage_text:<26}] {pct:3d}% | fps {fps_text:>8} | "
            f"eta {_fmt_seconds(eta):>8} | elapsed {_fmt_seconds(elapsed):>8}"
        )
        padded = line
        if len(line) < state["line_len"]:
            padded = line + (" " * (state["line_len"] - len(line)))
        print(f"\r{padded}", end="", flush=True)
        state["line_len"] = max(state["line_len"], len(line))
        state["last_emit"] = now
        state["last_stage"] = stage
        state["last_progress"] = progress

    result = run_local_serial(
        input_path=args.input,
        output_path=args.output,
        output_dir=args.output_dir,
        runner=args.runner,
        quality_tier=args.quality,
        detector_model=args.detector,
        restorer_model=args.restorer,
        refiner_model=args.refiner,
        duration_hint_seconds=args.duration_hint_seconds,
        options=options,
        on_progress=_on_progress,
    )

    if state["line_len"] > 0:
        print()
    if args.json:
        _print(_local_result_to_dict(result))
    else:
        _print_local_human(result)


def _cmd_setup_models(args: argparse.Namespace) -> None:
    result = setup_models(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        force=args.force,
        dry_run=args.dry_run,
    )
    if args.json:
        _print(_setup_result_to_dict(result))
    else:
        _print_setup_human(result)

    if result.failed and not args.allow_partial:
        raise RuntimeError(
            f"{len(result.failed)} model(s) failed. Re-run with --allow-partial to ignore failures."
        )


def _cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    from vistora.app.main import create_app
    from vistora.app.settings import load_settings

    settings = load_settings()
    host = args.host or settings.host
    port = args.port or settings.port
    uvicorn.run(create_app(settings=settings), host=host, port=port, reload=args.reload, log_level="info")


def _cmd_health(args: argparse.Namespace) -> None:
    _print(_request(args.base_url, "GET", "/healthz", args.timeout))


def _cmd_capabilities(args: argparse.Namespace) -> None:
    _print(_request(args.base_url, "GET", "/api/v1/system/capabilities", args.timeout))


def _cmd_models(args: argparse.Namespace) -> None:
    _print(_request(args.base_url, "GET", "/api/v1/models/catalog", args.timeout))


def _cmd_jobs_create(args: argparse.Namespace) -> None:
    options = _parse_json_object(args.options, "options")
    payload: dict[str, Any] = {
        "input_path": args.input,
        "output_path": args.output,
        "user_id": args.user,
        "profile_name": args.profile,
        "runner": args.runner,
        "quality_tier": args.quality,
        "detector_model": args.detector,
        "restorer_model": args.restorer,
        "refiner_model": args.refiner,
        "options": options,
    }
    if args.estimated_credits is not None:
        payload["estimated_credits"] = args.estimated_credits
    if args.duration_hint_seconds is not None:
        payload["duration_hint_seconds"] = args.duration_hint_seconds
    _print(_request(args.base_url, "POST", "/api/v1/jobs", args.timeout, payload))


def _cmd_jobs_list(args: argparse.Namespace) -> None:
    result = _request(args.base_url, "GET", "/api/v1/jobs", args.timeout)
    if args.user:
        jobs = [job for job in result.get("jobs", []) if job.get("user_id") == args.user]
        result = {"jobs": jobs}
    _print(result)


def _cmd_jobs_get(args: argparse.Namespace) -> None:
    _print(_request(args.base_url, "GET", f"/api/v1/jobs/{args.job_id}", args.timeout))


def _cmd_jobs_cancel(args: argparse.Namespace) -> None:
    _print(_request(args.base_url, "POST", f"/api/v1/jobs/{args.job_id}/cancel", args.timeout))


def _cmd_credits_balance(args: argparse.Namespace) -> None:
    _print(_request(args.base_url, "GET", f"/api/v1/credits/{urllib.parse.quote(args.user_id)}", args.timeout))


def _cmd_credits_topup(args: argparse.Namespace) -> None:
    payload = {"amount": args.amount, "reason": args.reason}
    path = f"/api/v1/credits/{urllib.parse.quote(args.user_id)}/topup"
    _print(_request(args.base_url, "POST", path, args.timeout, payload))


def _cmd_credits_transactions(args: argparse.Namespace) -> None:
    path = f"/api/v1/credits/{urllib.parse.quote(args.user_id)}/transactions"
    _print(_request(args.base_url, "GET", path, args.timeout))


def _cmd_profiles_list(args: argparse.Namespace) -> None:
    _print(_request(args.base_url, "GET", "/api/v1/profiles", args.timeout))


def _cmd_profiles_get(args: argparse.Namespace) -> None:
    path = f"/api/v1/profiles/{urllib.parse.quote(args.name)}"
    _print(_request(args.base_url, "GET", path, args.timeout))


def _cmd_profiles_put(args: argparse.Namespace) -> None:
    settings = _parse_json_object(args.settings, "settings")
    path = f"/api/v1/profiles/{urllib.parse.quote(args.name)}"
    _print(_request(args.base_url, "PUT", path, args.timeout, {"settings": settings}))


def _cmd_tg_send(args: argparse.Namespace) -> None:
    payload = _parse_json_object(args.payload, "payload")
    req = {"event": args.event, "user_id": args.user_id, "payload": payload}
    _print(_request(args.base_url, "POST", "/api/v1/tg/webhook", args.timeout, req))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vistora CLI")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="API base URL, default from VISTORA_BASE_URL or http://127.0.0.1:8585",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run one local restoration task serially (no worker queue)")
    p_run.add_argument("input", help="Input video/file path")
    p_run.add_argument("-o", "--output", default=None, help="Output file path. If omitted, auto-generated under output-dir.")
    p_run.add_argument("--output-dir", default="outputs", help="Default output directory when --output is omitted")
    p_run.add_argument("--runner", default="auto", choices=["auto", "dry-run", "lada-cli"])
    p_run.add_argument("--quality", default="ultra", choices=["balanced", "high", "ultra"])
    p_run.add_argument("--detector", default=None, help="Detector model id override")
    p_run.add_argument("--restorer", default=None, help="Restorer model id override")
    p_run.add_argument("--refiner", default=None, help="Refiner model id override")
    p_run.add_argument("--duration-hint-seconds", type=int, default=None, help="Duration hint for progress and ETA")
    p_run.add_argument("--option", action="append", default=[], help="Extra runner option KEY=VALUE, can repeat")
    p_run.add_argument("--options-json", default="{}", help="Extra runner options as JSON object")
    p_run.add_argument("--progress-interval", type=float, default=0.2, help="Progress refresh interval in seconds")
    p_run.add_argument("--json", action="store_true", help="Print final result as JSON")
    p_run.set_defaults(func=_cmd_run)

    p_setup = sub.add_parser("setup-models", help="Prepare model files from a manifest")
    p_setup.add_argument("--manifest", default="models/manifest.json", help="Model manifest JSON path")
    p_setup.add_argument("--output-dir", default="models/assets", help="Output directory for model files")
    p_setup.add_argument("--force", action="store_true", help="Re-download even when output file exists")
    p_setup.add_argument("--dry-run", action="store_true", help="Validate manifest and print planned downloads only")
    p_setup.add_argument("--allow-partial", action="store_true", help="Do not fail command when some models fail")
    p_setup.add_argument("--json", action="store_true", help="Print result as JSON")
    p_setup.set_defaults(func=_cmd_setup_models)

    p_serve = sub.add_parser("serve", help="Start local Vistora web/API service")
    p_serve.add_argument("--host", default=None, help="Bind host, default from settings/env")
    p_serve.add_argument("--port", type=int, default=None, help="Bind port, default from settings/env")
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload")
    p_serve.set_defaults(func=_cmd_serve)

    p_health = sub.add_parser("health", help="Check service health")
    p_health.set_defaults(func=_cmd_health)

    p_caps = sub.add_parser("capabilities", help="Show system capabilities")
    p_caps.set_defaults(func=_cmd_capabilities)

    p_models = sub.add_parser("models", help="Show model catalog")
    p_models.set_defaults(func=_cmd_models)

    p_jobs = sub.add_parser("jobs", help="Job operations")
    jobs_sub = p_jobs.add_subparsers(dest="jobs_command", required=True)

    p_jobs_create = jobs_sub.add_parser("create", help="Create a job")
    p_jobs_create.add_argument("--input", required=True, help="Input video/file path")
    p_jobs_create.add_argument("--output", default=None, help="Output video path")
    p_jobs_create.add_argument("--user", default="anonymous", help="User id")
    p_jobs_create.add_argument("--profile", default=None, help="Profile name")
    p_jobs_create.add_argument("--runner", default="auto", choices=["auto", "dry-run", "lada-cli"])
    p_jobs_create.add_argument("--quality", default="ultra", choices=["balanced", "high", "ultra"])
    p_jobs_create.add_argument("--detector", default=None, help="Detector model id")
    p_jobs_create.add_argument("--restorer", default=None, help="Restorer model id")
    p_jobs_create.add_argument("--refiner", default=None, help="Refiner model id")
    p_jobs_create.add_argument("--estimated-credits", type=int, default=None)
    p_jobs_create.add_argument("--duration-hint-seconds", type=int, default=None)
    p_jobs_create.add_argument("--options", default="{}", help="JSON object for runner options")
    p_jobs_create.set_defaults(func=_cmd_jobs_create)

    p_jobs_list = jobs_sub.add_parser("list", help="List jobs")
    p_jobs_list.add_argument("--user", default=None, help="Filter by user id")
    p_jobs_list.set_defaults(func=_cmd_jobs_list)

    p_jobs_get = jobs_sub.add_parser("get", help="Get job detail")
    p_jobs_get.add_argument("job_id")
    p_jobs_get.set_defaults(func=_cmd_jobs_get)

    p_jobs_cancel = jobs_sub.add_parser("cancel", help="Cancel queued/running job")
    p_jobs_cancel.add_argument("job_id")
    p_jobs_cancel.set_defaults(func=_cmd_jobs_cancel)

    p_credits = sub.add_parser("credits", help="Credit operations")
    credits_sub = p_credits.add_subparsers(dest="credits_command", required=True)

    p_balance = credits_sub.add_parser("balance", help="Query user balance")
    p_balance.add_argument("user_id")
    p_balance.set_defaults(func=_cmd_credits_balance)

    p_topup = credits_sub.add_parser("topup", help="Topup user credits")
    p_topup.add_argument("user_id")
    p_topup.add_argument("amount", type=int)
    p_topup.add_argument("--reason", default="manual_topup")
    p_topup.set_defaults(func=_cmd_credits_topup)

    p_txns = credits_sub.add_parser("transactions", help="List credit transactions")
    p_txns.add_argument("user_id")
    p_txns.set_defaults(func=_cmd_credits_transactions)

    p_profiles = sub.add_parser("profiles", help="Profile operations")
    profiles_sub = p_profiles.add_subparsers(dest="profiles_command", required=True)

    p_profiles_list = profiles_sub.add_parser("list", help="List profiles")
    p_profiles_list.set_defaults(func=_cmd_profiles_list)

    p_profiles_get = profiles_sub.add_parser("get", help="Get profile detail")
    p_profiles_get.add_argument("name")
    p_profiles_get.set_defaults(func=_cmd_profiles_get)

    p_profiles_put = profiles_sub.add_parser("put", help="Create or update profile")
    p_profiles_put.add_argument("name")
    p_profiles_put.add_argument("--settings", required=True, help="JSON object")
    p_profiles_put.set_defaults(func=_cmd_profiles_put)

    p_tg = sub.add_parser("tg", help="Telegram webhook test operations")
    tg_sub = p_tg.add_subparsers(dest="tg_command", required=True)

    p_tg_send = tg_sub.add_parser("send", help="Send webhook event")
    p_tg_send.add_argument("--event", required=True, choices=["ping", "balance", "topup"])
    p_tg_send.add_argument("--user-id", default="anonymous")
    p_tg_send.add_argument("--payload", default="{}")
    p_tg_send.set_defaults(func=_cmd_tg_send)

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
