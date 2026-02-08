from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


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
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL, default from VISTORA_BASE_URL or http://127.0.0.1:8585")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    sub = parser.add_subparsers(dest="command", required=True)

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
    p_jobs_create.add_argument("--runner", default="dry-run", choices=["dry-run", "lada-cli"])
    p_jobs_create.add_argument("--quality", default="high", choices=["balanced", "high", "ultra"])
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

    p_jobs_cancel = jobs_sub.add_parser("cancel", help="Cancel queued job")
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
