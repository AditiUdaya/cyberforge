"""Black-box contract tests: each route, each status code, schema-valid replies (--target).

Every reply is checked against shared/contract/*.schema.json, which copies PRD Appendix A.
The checks talk only HTTP, so the same list runs against the in-process app (api tests),
a local server (--target local) or the deployed HTTPS address (--target https://...).

Owner: B. Filled in by: B1.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parent.parent
CONTRACT_DIR = REPO / "shared" / "contract"


class Response(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def headers(self) -> Mapping[str, str]: ...

    @property
    def text(self) -> str: ...

    def json(self) -> Any: ...


class Client(Protocol):
    def get(self, url: str, *, params: Mapping[str, str] | None = None) -> Any: ...

    def post(
        self,
        url: str,
        *,
        json: Any = None,
        content: bytes | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any: ...


@dataclass(frozen=True)
class Result:
    name: str
    passed: bool
    detail: str


Check = Callable[[Client], None]
CHECKS: list[tuple[str, Check]] = []


def check(name: str) -> Callable[[Check], Check]:
    def register(fn: Check) -> Check:
        CHECKS.append((name, fn))
        return fn

    return register


def load_schema(name: str) -> dict[str, Any]:
    path = CONTRACT_DIR / f"{name}.schema.json"
    schema: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def expect(response: Response, status: int, schema: str) -> Any:
    """Assert status, JSON content type and schema; return the parsed body."""
    if response.status_code != status:
        raise AssertionError(f"status {response.status_code}, want {status}: {response.text[:200]}")
    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        raise AssertionError(f"content-type {content_type!r}, want application/json")
    body = response.json()
    errors = sorted(
        Draft202012Validator(load_schema(schema)).iter_errors(body), key=lambda e: list(e.path)
    )
    if errors:
        where = "/".join(str(p) for p in errors[0].path) or "(root)"
        raise AssertionError(f"{schema} at {where}: {errors[0].message}")
    return body


# PRD Appendix A examples, used as the valid bodies.
PRD_REPORT: dict[str, Any] = {
    "report_id": "rep_000123",
    "occurred_at": "2026-10-27T18:21:04+05:30",
    "reported_at": "2026-10-27T18:40:04+05:30",
    "reporter_id": "r_7c2d91aa",
    "ip_prefix": "103.21.58",
    "channel": "Phone call",
    "scam_type": "digital-arrest",
    "identifier_type": "phone",
    "identifier_value": "+91 98765 43210",
    "pincode": "560102",
    "locality": "HSR Layout",
    "city": "Bengaluru",
    "note": "Video call from a man in police uniform...",
    "has_screenshot": False,
    "amount_lost_inr": 0,
}

PRD_CHALLENGE: dict[str, Any] = {
    "identifier_type": "phone",
    "identifier_value": "+91 80 4100 2233",
    "claimant_name": "Fresh Bakes",
    "contact_email": "owner@example.com",
    "proof_note": "GST certificate and shop licence attached.",
}

REPORT_REQUIRED = load_schema("reports.request")["required"]


@check("GET /health is 200 {ok: true}")
def _health(c: Client) -> None:
    expect(c.get("/health"), 200, "health.reply")


@check("POST /admin/reset is 200 JSON")
def _reset(c: Client) -> None:
    expect(c.post("/admin/reset"), 200, "admin_reset.reply")


@check("POST /reports accepts the PRD example with 201")
def _report_ok(c: Client) -> None:
    body = expect(c.post("/reports", json=PRD_REPORT), 201, "reports.reply")
    if body["report_id"] != PRD_REPORT["report_id"]:
        raise AssertionError(f"report_id {body['report_id']!r}, want the one sent")


@check("POST /reports accepts extra fields and no ip_prefix")
def _report_extra(c: Client) -> None:
    sent = {k: v for k, v in PRD_REPORT.items() if k != "ip_prefix"}
    sent |= {"report_id": "rep_extra_1", "app_version": "web-1"}
    expect(c.post("/reports", json=sent), 201, "reports.reply")


@check("POST /reports with each required field missing is 400 {error}")
def _report_missing(c: Client) -> None:
    for field in REPORT_REQUIRED:
        sent = {k: v for k, v in PRD_REPORT.items() if k != field}
        try:
            expect(c.post("/reports", json=sent), 400, "error")
        except AssertionError as e:
            raise AssertionError(f"without {field}: {e}") from e


@check("POST /reports with a non-JSON body is 400 {error}")
def _report_not_json(c: Client) -> None:
    response = c.post("/reports", content=b"not json", headers={"content-type": "application/json"})
    expect(response, 400, "error")


@check("POST /reports with an unknown identifier_type is 400 {error}")
def _report_bad_type(c: Client) -> None:
    expect(c.post("/reports", json=PRD_REPORT | {"identifier_type": "email"}), 400, "error")


@check("GET /lookup for each identifier type is 200 with a valid verdict")
def _lookup_ok(c: Client) -> None:
    for kind, value in [
        ("phone", "+91 98765 43210"),
        ("upi", "ravi12@okaxis"),
        ("url", "https://sbi-kyc.in/pay"),
        ("sender_id", "VM-HDFCBK"),
    ]:
        try:
            expect(c.get("/lookup", params={"type": kind, "value": value}), 200, "lookup.reply")
        except AssertionError as e:
            raise AssertionError(f"{kind}: {e}") from e


@check("GET /lookup without type or value is 400 {error}")
def _lookup_missing(c: Client) -> None:
    expect(c.get("/lookup", params={"value": "+91 98765 43210"}), 400, "error")
    expect(c.get("/lookup", params={"type": "phone"}), 400, "error")


@check("GET /lookup with an unknown type is 400 {error}")
def _lookup_bad_type(c: Client) -> None:
    expect(c.get("/lookup", params={"type": "email", "value": "a@b.c"}), 400, "error")


@check("GET /map with defaults and with days, radius_km is 200")
def _map_ok(c: Client) -> None:
    expect(c.get("/map", params={"pincode": "560102"}), 200, "map.reply")
    params = {"pincode": "560102", "days": "7", "radius_km": "2"}
    expect(c.get("/map", params=params), 200, "map.reply")


@check("GET /map without pincode is 400 {error}")
def _map_missing(c: Client) -> None:
    expect(c.get("/map"), 400, "error")


@check("GET /map with non-numeric days is 400 {error}")
def _map_bad_days(c: Client) -> None:
    expect(c.get("/map", params={"pincode": "560102", "days": "week"}), 400, "error")


@check("GET /alerts is 200 {alerts: [...]}")
def _alerts_ok(c: Client) -> None:
    expect(c.get("/alerts", params={"pincode": "560102"}), 200, "alerts.reply")


@check("GET /alerts without pincode is 400 {error}")
def _alerts_missing(c: Client) -> None:
    expect(c.get("/alerts"), 400, "error")


@check("POST /challenges accepts the PRD example with 201 under_review")
def _challenge_ok(c: Client) -> None:
    expect(c.post("/challenges", json=PRD_CHALLENGE), 201, "challenges.reply")


@check("POST /challenges without claimant_name is 400 {error}")
def _challenge_missing(c: Client) -> None:
    sent = {k: v for k, v in PRD_CHALLENGE.items() if k != "claimant_name"}
    expect(c.post("/challenges", json=sent), 400, "error")


@check("GET /license is 200 with licensee, expires_at, valid")
def _license_get(c: Client) -> None:
    expect(c.get("/license"), 200, "license_get.reply")


@check("POST /license with a missing signature is 400 {error}")
def _license_missing(c: Client) -> None:
    sent = {"licensee": "Demo Bank", "expires_at": "2026-11-15T10:05:00+05:30"}
    expect(c.post("/license", json=sent), 400, "error")


@check("An unknown route is 404 {error}")
def _unknown(c: Client) -> None:
    expect(c.get("/no-such-route"), 404, "error")


@check("A wrong method is 405 {error}")
def _wrong_method(c: Client) -> None:
    expect(c.post("/health"), 405, "error")


@check("Replies never echo reporter_id, ip_prefix or the note")
def _no_echo(c: Client) -> None:
    sent = PRD_REPORT | {"report_id": "rep_echo_1"}
    replies = [
        c.post("/reports", json=sent).text,
        c.get("/lookup", params={"type": "phone", "value": "+91 98765 43210"}).text,
    ]
    for secret in (sent["reporter_id"], sent["ip_prefix"], sent["note"]):
        for reply in replies:
            if secret in reply:
                raise AssertionError(f"reply contains a reporter field: {secret!r}")


@check("400 messages name the field but never echo what was sent")
def _no_echo_in_errors(c: Client) -> None:
    marker = "zz-secret-zz"
    sent = PRD_REPORT | {"identifier_type": marker, "reporter_id": marker + "-r"}
    body = expect(c.post("/reports", json=sent), 400, "error")
    if marker in body["error"]:
        raise AssertionError(f"error message echoes the input: {body['error']!r}")
    response = c.get("/lookup", params={"type": marker, "value": marker})
    if marker in expect(response, 400, "error")["error"]:
        raise AssertionError("lookup error message echoes the query")


def run(client: Client) -> list[Result]:
    results = []
    for name, fn in CHECKS:
        try:
            fn(client)
        except AssertionError as e:
            results.append(Result(name, False, str(e)))
        else:
            results.append(Result(name, True, ""))
    return results


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


@contextmanager
def local_server() -> Iterator[str]:
    """Start the API from ../api on a free port with a throwaway database.

    Runs the API venv's Python directly rather than through `uv run`: on Windows, stopping
    `uv` leaves its uvicorn child running.
    """
    python = _api_python()
    port = _free_port()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        env = os.environ | {"SCAM_MAP_DB_PATH": str(Path(tmp) / "contract.sqlite")}
        args = [
            str(python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--port",
            str(port),
            "--no-access-log",
            "--log-level",
            "warning",
        ]
        proc = subprocess.Popen(args, cwd=REPO / "api", env=env)
        try:
            base = f"http://127.0.0.1:{port}"
            _wait_ready(base, proc)
            yield base
        finally:
            proc.terminate()
            proc.wait(timeout=10)


def _api_python() -> Path:
    """The API venv's interpreter, creating the venv from uv.lock if it is missing."""
    api = REPO / "api"
    venv = api / ".venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        uv = shutil.which("uv")
        if uv is None:
            raise SystemExit("uv is not on PATH and api/.venv does not exist")
        subprocess.run([uv, "sync", "--frozen"], cwd=api, check=True)
    return python


def _wait_ready(base: str, proc: subprocess.Popen[bytes]) -> None:
    import httpx

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"API exited with code {proc.returncode}")
        try:
            if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(0.2)
    raise SystemExit("API did not answer /health within 30 s")


def _report(results: list[Result], target: str) -> int:
    failed = [r for r in results if not r.passed]
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL'}  {r.name}")
        if not r.passed:
            print(f"      {r.detail}")
    print(f"\n{len(results) - len(failed)}/{len(results)} contract checks passed against {target}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    import httpx

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "--target", required=True, help="'local' or a base URL such as https://host"
    )
    args = parser.parse_args(argv)

    if args.target == "local":
        with local_server() as base, httpx.Client(base_url=base, timeout=10) as client:
            return _report(run(client), f"local ({base})")
    with httpx.Client(base_url=args.target.rstrip("/"), timeout=10) as client:
        return _report(run(client), args.target)


if __name__ == "__main__":
    sys.exit(main())
