from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx

from .config import settings


@dataclass
class Token:
    access_token: str
    refresh_token: str
    expires_at: int  # unix epoch seconds
    token_type: str = "Bearer"
    scope: str = ""


def _now() -> int:
    return int(time.time())


def _read_json(path: str) -> Optional[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _write_json(path: str, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))


def load_token() -> Optional[Token]:
    data = _read_json(settings.YOTO_TOKEN_PATH)
    if not data:
        return None
    try:
        return Token(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=int(data["expires_at"]),
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope", ""),
        )
    except Exception:
        return None


def save_token(t: Token) -> None:
    _write_json(
        settings.YOTO_TOKEN_PATH,
        {
            "access_token": t.access_token,
            "refresh_token": t.refresh_token,
            "expires_at": t.expires_at,
            "token_type": t.token_type,
            "scope": t.scope,
        },
    )


def load_device() -> Optional[dict[str, Any]]:
    return _read_json(settings.YOTO_DEVICE_PATH)


def save_device(d: dict[str, Any]) -> None:
    _write_json(settings.YOTO_DEVICE_PATH, d)


async def _oauth_device_start(client: httpx.AsyncClient) -> dict[str, Any]:
    url = f"{settings.YOTO_LOGIN_BASE}/oauth/device/code"
    data = {
        "client_id": settings.YOTO_CLIENT_ID,
    }
    if settings.YOTO_SCOPE:
        data["scope"] = settings.YOTO_SCOPE

    resp = await client.post(url, data=data)
    resp.raise_for_status()
    payload = resp.json()
    # expected fields:
    # device_code, user_code, verification_uri, verification_uri_complete, expires_in, interval
    save_device(payload)
    return payload


async def _oauth_device_poll(client: httpx.AsyncClient, device_code: str) -> dict[str, Any]:
    url = f"{settings.YOTO_LOGIN_BASE}/oauth/token"
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "device_code": device_code,
        "client_id": settings.YOTO_CLIENT_ID,
    }
    resp = await client.post(url, data=data)
    # success is 200; pending/slowdown/errors usually 400 with json {error: ...}
    if resp.status_code == 200:
        return resp.json()
    try:
        return resp.json()
    except Exception:
        return {"error": "unknown_error", "raw": resp.text}


async def _oauth_refresh(client: httpx.AsyncClient, refresh_token: str) -> dict[str, Any]:
    url = f"{settings.YOTO_LOGIN_BASE}/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.YOTO_CLIENT_ID,
    }
    resp = await client.post(url, data=data)
    resp.raise_for_status()
    return resp.json()


def _token_from_payload(payload: dict[str, Any]) -> Token:
    expires_in = int(payload.get("expires_in", 3600))
    return Token(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token") or payload.get("refresh_token", ""),
        expires_at=_now() + expires_in - 30,  # small safety buffer
        token_type=payload.get("token_type", "Bearer"),
        scope=payload.get("scope", ""),
    )


async def ensure_token() -> Token:
    """
    Returns a valid access token, refreshing if needed.
    Raises RuntimeError if not authenticated yet.
    """
    t = load_token()
    if not t:
        raise RuntimeError("Not authenticated")

    if t.expires_at > _now():
        return t

    async with httpx.AsyncClient(timeout=30) as client:
        refreshed = await _oauth_refresh(client, t.refresh_token)
        newt = _token_from_payload(refreshed)
        # some providers don't return refresh_token on refresh; keep old if missing
        if not newt.refresh_token:
            newt.refresh_token = t.refresh_token
        save_token(newt)
        return newt


async def auth_start() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        payload = await _oauth_device_start(client)
        return {
            "verification_uri_complete": payload.get("verification_uri_complete"),
            "verification_uri": payload.get("verification_uri"),
            "user_code": payload.get("user_code"),
            "interval": payload.get("interval", 5),
            "expires_in": payload.get("expires_in"),
        }


async def auth_status() -> dict[str, Any]:
    # if token exists and valid -> authenticated
    t = load_token()
    if t and t.expires_at > _now():
        return {"authenticated": True, "expires_at": t.expires_at}

    # if token exists but expired, try refresh
    if t:
        try:
            t2 = await ensure_token()
            return {"authenticated": True, "expires_at": t2.expires_at}
        except Exception:
            pass

    # else poll device flow if we have a device_code
    dev = load_device()
    if not dev or not dev.get("device_code"):
        return {"authenticated": False}

    device_code = dev["device_code"]
    interval = int(dev.get("interval", 5))
    expires_in = int(dev.get("expires_in", 600))
    created_at = int(dev.get("created_at") or _now())
    # store created_at if missing
    if "created_at" not in dev:
        dev["created_at"] = created_at
        save_device(dev)

    if _now() > created_at + expires_in:
        return {"authenticated": False, "error": "device_code_expired"}

    async with httpx.AsyncClient(timeout=30) as client:
        payload = await _oauth_device_poll(client, device_code)

    if "access_token" in payload:
        token = _token_from_payload(payload)
        # keep refresh token if provider returns it; if not, we can't refresh later
        if not token.refresh_token and t and t.refresh_token:
            token.refresh_token = t.refresh_token
        save_token(token)
        return {"authenticated": True, "expires_at": token.expires_at}

    err = payload.get("error")
    if err in ("authorization_pending", "slow_down"):
        return {
            "pending": True,
            "verification_uri_complete": dev.get("verification_uri_complete"),
            "verification_uri": dev.get("verification_uri"),
            "user_code": dev.get("user_code"),
            "interval": interval if err != "slow_down" else max(interval + 2, 7),
        }

    return {"authenticated": False, "error": err or "unknown"}


async def _api_request(method: str, path: str, token: Token, **kwargs: Any) -> httpx.Response:
    url = f"{settings.YOTO_API_BASE}{path}"
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token.access_token}"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.request(method, url, headers=headers, **kwargs)
        return resp


async def get_upload_url(filename: str, token: Token) -> dict[str, Any]:
    # Based on your description:
    # GET /media/transcode/audio/uploadUrl
    resp = await _api_request(
        "GET",
        "/media/transcode/audio/uploadUrl",
        token,
        params={"filename": filename},
    )
    resp.raise_for_status()
    return resp.json()


async def put_presigned(upload_url: str, content: bytes, content_type: str = "audio/mpeg") -> None:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.put(upload_url, content=content, headers={"Content-Type": content_type})
        r.raise_for_status()


async def poll_transcode(upload_id: str, token: Token, timeout_s: int = 180) -> dict[str, Any]:
    start = time.time()
    while True:
        resp = await _api_request("GET", f"/media/upload/{upload_id}/transcoded", token)
        if resp.status_code == 200:
            payload = resp.json()
            # Expect payload has sha or similar when ready
            return payload

        if time.time() - start > timeout_s:
            raise RuntimeError("Transcode timed out")

        await asyncio.sleep(3)


async def download_audio(url: str, max_mb: int = 200) -> bytes:
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        content = r.content
        if len(content) > max_mb * 1024 * 1024:
            raise RuntimeError(f"Audio too large (> {max_mb}MB)")
        return content


async def upload_episode_audio(audio_url: str, title: str) -> dict[str, Any]:
    token = await ensure_token()

    # 1) download audio
    audio = await download_audio(audio_url)

    # 2) get presigned upload URL
    safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title).strip() or "episode"
    filename = f"{safe_name}.mp3"
    info = await get_upload_url(filename, token)

    upload_url = info.get("uploadUrl") or info.get("upload_url") or info.get("url")
    upload_id = info.get("uploadId") or info.get("upload_id") or info.get("id")
    if not upload_url or not upload_id:
        raise RuntimeError(f"Unexpected uploadUrl response: {info}")

    # 3) PUT to S3
    await put_presigned(upload_url, audio, content_type="audio/mpeg")

    # 4) poll transcode
    transcoded = await poll_transcode(str(upload_id), token)

    return {
        "uploadId": str(upload_id),
        "transcoded": transcoded,
    }
