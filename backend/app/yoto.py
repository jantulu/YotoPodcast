# app/yoto.py
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import httpx

YOTO_API_BASE = os.getenv("YOTO_API_BASE", "https://api.yotoplay.com").rstrip("/")
YOTO_LOGIN_BASE = os.getenv("YOTO_LOGIN_BASE", "https://login.yotoplay.com").rstrip("/")

YOTO_CLIENT_ID = os.getenv("YOTO_CLIENT_ID", "").strip()
YOTO_SCOPE = os.getenv("YOTO_SCOPE", "").strip()

# Single shared token/device state (per your "same auth for everyone" requirement)
YOTO_TOKEN_PATH = os.getenv("YOTO_TOKEN_PATH", "/data/yoto_token.json")
YOTO_DEVICE_PATH = os.getenv("YOTO_DEVICE_PATH", "/data/yoto_device.json")


# ----------------------------
# Persistence helpers
# ----------------------------
def _read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        p = Path(path)
        if not p.exists():
            return None
        return json.loads(p.read_text())
    except Exception:
        return None


def _write_json(path: str, data: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True))


def _now() -> int:
    return int(time.time())


def load_token() -> Optional[Dict[str, Any]]:
    return _read_json(YOTO_TOKEN_PATH)


def save_token(token: Dict[str, Any]) -> None:
    _write_json(YOTO_TOKEN_PATH, token)


def clear_token() -> None:
    try:
        Path(YOTO_TOKEN_PATH).unlink(missing_ok=True)
    except Exception:
        pass


def load_device_flow() -> Optional[Dict[str, Any]]:
    return _read_json(YOTO_DEVICE_PATH)


def save_device_flow(device: Dict[str, Any]) -> None:
    _write_json(YOTO_DEVICE_PATH, device)


def clear_device_flow() -> None:
    try:
        Path(YOTO_DEVICE_PATH).unlink(missing_ok=True)
    except Exception:
        pass


def is_token_valid(tok: Dict[str, Any]) -> bool:
    exp = tok.get("expires_at")
    if not exp:
        return False
    return int(exp) > _now() + 30  # 30s margin


# ----------------------------
# HTTP client helpers
# ----------------------------
def _client(timeout: float = 60.0, headers: Optional[Dict[str, str]] = None) -> httpx.AsyncClient:
    # Don't use http2=True unless you install httpx[http2] (h2 dependency)
    return httpx.AsyncClient(timeout=httpx.Timeout(timeout), headers=headers)


async def _raise_for_status_with_body(r: httpx.Response) -> None:
    if r.status_code < 400:
        return
    try:
        body = r.json()
    except Exception:
        body = r.text
    raise RuntimeError(f"HTTP {r.status_code} for {r.request.method} {r.request.url}: {body}")


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)


async def yoto_authed_client(timeout: float = 60.0) -> httpx.AsyncClient:
    tok = load_token()
    if not tok:
        raise RuntimeError("Not authenticated (no token stored).")

    # If expired, try refresh (best effort)
    if not is_token_valid(tok):
        await oauth_refresh_if_possible()
        tok = load_token()

    if not tok or not is_token_valid(tok):
        raise RuntimeError("Not authenticated (missing or expired token).")

    headers = {"Authorization": f"Bearer {tok['access_token']}"}
    return _client(timeout=timeout, headers=headers)


# ----------------------------
# OAuth refresh support
# ----------------------------
async def oauth_refresh_if_possible() -> Dict[str, Any]:
    """
    Best-effort refresh. If no refresh_token, returns {refreshed: False}.
    If refresh succeeds, updates stored token and returns {refreshed: True}.
    """
    tok = load_token()
    if not tok:
        return {"refreshed": False, "reason": "no_token"}

    refresh_token = tok.get("refresh_token")
    if not refresh_token:
        return {"refreshed": False, "reason": "no_refresh_token"}

    if not YOTO_CLIENT_ID:
        return {"refreshed": False, "reason": "missing_client_id"}

    url = f"{YOTO_LOGIN_BASE}/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": YOTO_CLIENT_ID,
    }

    async with _client(timeout=30) as client:
        r = await client.post(url, data=payload)

    if r.status_code != 200:
        # If refresh fails, clear token to force re-auth (avoids infinite bad token loops)
        try:
            body = r.json()
        except Exception:
            body = r.text
        clear_token()
        return {"refreshed": False, "reason": "refresh_failed", "status": r.status_code, "body": body}

    new_tok = r.json()
    expires_in = int(new_tok.get("expires_in") or 0)
    new_tok["expires_at"] = _now() + expires_in

    # Some providers don't re-issue refresh_token every time; preserve old one if missing
    if not new_tok.get("refresh_token") and refresh_token:
        new_tok["refresh_token"] = refresh_token

    save_token(new_tok)
    return {"refreshed": True, "expires_at": int(new_tok["expires_at"])}


# ----------------------------
# OAuth Device Flow
# ----------------------------
def _device_expired(dev: Dict[str, Any]) -> bool:
    expires_in = int(dev.get("expires_in") or 0)
    requested_at = int(dev.get("requested_at") or 0)
    if expires_in and requested_at and (_now() > requested_at + expires_in):
        return True
    return False


async def oauth_device_start() -> Dict[str, Any]:
    if not YOTO_CLIENT_ID:
        raise RuntimeError("YOTO_CLIENT_ID is not set. Set it in .env / docker compose environment.")

    url = f"{YOTO_LOGIN_BASE}/oauth/device/code"
    payload: Dict[str, Any] = {"client_id": YOTO_CLIENT_ID}
    if YOTO_SCOPE:
        payload["scope"] = YOTO_SCOPE

    async with _client(timeout=30) as client:
        r = await client.post(url, data=payload)

    if r.status_code >= 400:
        try:
            body = r.json()
        except Exception:
            body = r.text
        raise RuntimeError(f"Device start failed: {r.status_code} {body}")

    data = r.json()

    interval = int(data.get("interval") or 5)
    requested_at = _now()

    device = {
        "device_code": data.get("device_code") or data.get("deviceCode"),
        "user_code": data.get("user_code") or data.get("userCode"),
        "verification_uri": data.get("verification_uri") or data.get("verificationUri"),
        "verification_uri_complete": data.get("verification_uri_complete") or data.get("verificationUriComplete"),
        "expires_in": int(data.get("expires_in") or 0),
        "interval": interval,
        "requested_at": requested_at,
        # enforce polling interval server-side so UI can't DOS your auth
        "next_poll_at": requested_at,  # allow immediate first poll
        "polls": 0,
    }

    if not device["device_code"]:
        raise RuntimeError(f"Device start response missing device_code: {data}")

    save_device_flow(device)
    return device


async def generate_one_time_auth_code() -> Dict[str, Any]:
    """
    Starts the OAuth device flow and generates a short one-time code that can be
    shown to users or used by tooling. The one-time code is stored alongside the
    device flow in `YOTO_DEVICE_PATH` so subsequent polling functions can locate
    the device_code.

    Returns a dict with `one_time_code`, `verification_uri` and
    `verification_uri_complete` (when available).
    """
    # Start the device flow (this saves the device object already)
    device = await oauth_device_start()

    # Generate a short, URL-safe code (6 chars is compact but may be adjusted)
    import secrets

    one_time = secrets.token_urlsafe(6)

    # Persist the one-time code into the saved device flow so other helpers can find it
    dev = load_device_flow() or {}
    dev["one_time_code"] = one_time
    save_device_flow(dev)

    return {
        "one_time_code": one_time,
        "verification_uri": dev.get("verification_uri"),
        "verification_uri_complete": dev.get("verification_uri_complete"),
        "expires_in": dev.get("expires_in"),
        "interval": dev.get("interval", 5),
    }


async def oauth_device_poll_once() -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Returns (authenticated, token_if_authed, meta)
      - meta may include: pending, slow_down, retry_after, error, expired
    Never raises for normal device-flow states.
    """
    dev = load_device_flow()
    if not dev:
        return False, None, {"missing_device": True}

    if _device_expired(dev):
        clear_device_flow()
        return False, None, {"expired": True}

    if not YOTO_CLIENT_ID:
        # configuration error *is* fatal
        raise RuntimeError("YOTO_CLIENT_ID is not set.")

    # Enforce interval / backoff
    now = _now()
    next_poll_at = int(dev.get("next_poll_at") or 0)
    interval = int(dev.get("interval") or 5)

    if now < next_poll_at:
        return False, None, {"pending": True, "retry_after": max(1, next_poll_at - now), "interval": interval}

    url = f"{YOTO_LOGIN_BASE}/oauth/token"
    payload = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "device_code": dev["device_code"],
        "client_id": YOTO_CLIENT_ID,
    }

    async with _client(timeout=30) as client:
        r = await client.post(url, data=payload)

    # update device poll accounting + schedule next allowed poll
    dev["polls"] = int(dev.get("polls") or 0) + 1
    dev["next_poll_at"] = now + interval
    save_device_flow(dev)

    if r.status_code == 200:
        tok = r.json()
        expires_in = int(tok.get("expires_in") or 0)
        tok["expires_at"] = _now() + expires_in
        save_token(tok)
        clear_device_flow()
        return True, tok, None

    # Expected pending states often come as 400/403/429 with JSON body containing "error"
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text}

    err = body.get("error")
    err_desc = body.get("error_description")

    if err == "authorization_pending":
        # keep waiting, tell caller when to retry
        return False, None, {"pending": True, "retry_after": interval, "interval": interval}

    if err == "slow_down":
        # back off (OAuth spec suggests increasing interval)
        interval = interval + 5
        dev["interval"] = interval
        dev["next_poll_at"] = _now() + interval
        save_device_flow(dev)
        return False, None, {"pending": True, "slow_down": True, "retry_after": interval, "interval": interval}

    if err in ("expired_token", "access_denied", "invalid_grant"):
        clear_device_flow()
        return False, None, {"pending": False, "error": err, "error_description": err_desc, "terminal": True}

    # Some providers use different codes; if it's any OAuth-ish error, return it cleanly
    if err:
        return False, None, {"pending": False, "error": err, "error_description": err_desc, "status": r.status_code}

    # Unknown non-JSON or unexpected response -> keep this fatal so you notice
    raise RuntimeError(f"Device poll failed: {r.status_code} {body}")


async def oauth_device_status() -> Dict[str, Any]:
    # If token valid, we're authenticated
    tok = load_token()
    if tok and is_token_valid(tok):
        return {"authenticated": True, "expires_at": int(tok["expires_at"])}

    # If token exists but expired, attempt refresh (best effort)
    if tok and not is_token_valid(tok):
        await oauth_refresh_if_possible()
        tok2 = load_token()
        if tok2 and is_token_valid(tok2):
            return {"authenticated": True, "expires_at": int(tok2["expires_at"]), "refreshed": True}

    dev = load_device_flow()
    if not dev:
        return {"authenticated": False}

    if _device_expired(dev):
        clear_device_flow()
        return {"authenticated": False}

    # Poll once (but safe — doesn't throw for pending/slow_down)
    authed, tok3, meta = await oauth_device_poll_once()
    if authed and tok3:
        return {"authenticated": True, "expires_at": int(tok3["expires_at"])}

    # pending path: return info so UI can display code + respect retry_after
    meta = meta or {}
    dev2 = load_device_flow() or dev
    return {
        "authenticated": False,
        "pending": bool(meta.get("pending", True)),
        "retry_after": int(meta.get("retry_after") or int(dev2.get("interval") or 5)),
        "interval": int(dev2.get("interval") or 5),
        "verification_uri": dev2.get("verification_uri"),
        "verification_uri_complete": dev2.get("verification_uri_complete"),
        "user_code": dev2.get("user_code"),
        "expires_in": dev2.get("expires_in"),
        "polls": int(dev2.get("polls") or 0),
        # include any non-terminal error details for debugging
        "error": meta.get("error"),
        "error_description": meta.get("error_description"),
        "status": meta.get("status"),
        "slow_down": bool(meta.get("slow_down", False)),
    }


# Backwards-compatible alias (some main.py versions import this)
async def oauth_device_poll() -> Dict[str, Any]:
    return await oauth_device_status()


# ----------------------------
# Yoto Media Upload + Transcode polling
# ----------------------------
@dataclass
class TranscodedResult:
    upload_id: str
    sha: str
    raw: Dict[str, Any]


async def request_audio_upload_url() -> Tuple[str, str]:
    async with await yoto_authed_client(timeout=60) as client:
        r = await client.get(f"{YOTO_API_BASE}/media/transcode/audio/uploadUrl")
        if r.status_code >= 400:
            try:
                body = r.json()
            except Exception:
                body = r.text
            raise RuntimeError(f"uploadUrl request failed: {r.status_code} {body}")
        data = r.json()

    upload = data.get("upload") or {}
    upload_url = upload.get("uploadUrl") or upload.get("url")
    upload_id = upload.get("uploadId") or upload.get("id")
    if not upload_url or not upload_id:
        raise RuntimeError(f"Unexpected uploadUrl response: {data}")
    return upload_url, upload_id


async def yoto_put_to_upload_url(upload_url: str, file_path: str, content_type: str) -> None:
    headers = {"Content-Type": content_type}

    async def file_iter(chunk_size: int = 1024 * 1024):
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    async with _client(timeout=900) as client:
        r = await client.put(upload_url, content=file_iter(), headers=headers)
        await _raise_for_status_with_body(r)


async def poll_transcoded(upload_id: str, timeout_s: int = 1800, poll_every_s: int = 3) -> TranscodedResult:
    deadline = time.time() + timeout_s
    url = f"{YOTO_API_BASE}/media/upload/{upload_id}/transcoded?loudnorm=false"

    async with await yoto_authed_client(timeout=60) as client:
        while time.time() < deadline:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                sha = (
                    data.get("sha")
                    or data.get("transcode", {}).get("sha")
                    or data.get("uploadSha256")
                )
                if sha:
                    return TranscodedResult(upload_id=upload_id, sha=str(sha), raw=data)

            elif r.status_code in (202, 204):
                pass
            else:
                try:
                    body = r.json()
                except Exception:
                    body = r.text
                raise RuntimeError(f"transcoded poll failed: {r.status_code} {body}")

            await _sleep(poll_every_s)

    raise RuntimeError(f"Timed out waiting for transcode uploadId={upload_id}")


async def upload_audio_to_yoto(file_path: str, mime_type: str = "audio/mpeg") -> TranscodedResult:
    upload_url, upload_id = await request_audio_upload_url()
    await yoto_put_to_upload_url(upload_url, file_path, content_type=mime_type)
    return await poll_transcoded(upload_id)
