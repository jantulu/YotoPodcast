from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .yoto import oauth_device_start, oauth_device_status, oauth_refresh_if_possible

app = FastAPI()

# -------------------------
# CORS
# -------------------------
# Example:
# CORS_ALLOW_ORIGINS=http://10.1.27.19:5173,http://localhost:5173
cors_origins = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()]
if not cors_origins:
    # sensible dev default
    cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://10.1.27.19:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Podcast API (example data)
# -------------------------

PODCASTS = [
    {"slug": "99pi", "title": "99% Invisible", "feedUrl": "https://feeds.simplecast.com/BqbsxVfO"},
    {"slug": "circle-round", "title": "Circle Round", "feedUrl": "https://rss.wbur.org/circleround/podcast"},
]

# Very small RSS parser via feed endpoint -> we’ll parse using a lightweight approach
# so you don't need extra deps. It supports common RSS item tags.
async def fetch_rss_episodes(feed_url: str, limit: int = 30) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=True) as client:
        r = await client.get(feed_url)
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"RSS fetch failed: {r.status_code}")

    xml = r.text

    # minimal parsing: use stdlib xml.etree
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"RSS parse failed: {e}")

    # RSS 2.0: <rss><channel><item>...
    channel = root.find("channel") if root.tag.lower().endswith("rss") else None
    if channel is None:
        # Atom feeds: <feed><entry>...
        # Not implementing Atom here, but can add if needed.
        raise HTTPException(status_code=502, detail="Unsupported feed format (expected RSS)")

    items = channel.findall("item") or []
    episodes: List[Dict[str, Any]] = []

    def _text(el: Optional[ET.Element]) -> str:
        if el is None or el.text is None:
            return ""
        return el.text.strip()

    for idx, item in enumerate(items[:limit]):
        title = _text(item.find("title"))
        desc = _text(item.find("description"))
        guid = _text(item.find("guid")) or f"item-{idx}"

        # enclosure is the common way to specify the audio file
        enclosure = item.find("enclosure")
        audio_url = enclosure.get("url") if enclosure is not None else ""
        if not audio_url:
            # sometimes link is audio, but usually not
            audio_url = _text(item.find("link"))

        episodes.append(
            {
                "id": guid,
                "title": title or f"Episode {idx+1}",
                "description": desc,
                "audioUrl": audio_url,
            }
        )

    return episodes


@app.get("/api/podcasts")
async def list_podcasts() -> List[Dict[str, Any]]:
    return PODCASTS


@app.get("/api/podcasts/{slug}/episodes")
async def list_episodes(slug: str) -> List[Dict[str, Any]]:
    p = next((p for p in PODCASTS if p["slug"] == slug), None)
    if not p:
        raise HTTPException(status_code=404, detail="Podcast not found")
    return await fetch_rss_episodes(p["feedUrl"], limit=50)


# -------------------------
# Yoto OAuth endpoints
# -------------------------

@app.get("/api/yoto/auth/status")
async def yoto_auth_status() -> Dict[str, Any]:
    # attempt refresh if expired and possible
    await oauth_refresh_if_possible()
    return token_diagnostics()


@app.post("/api/yoto/auth/start")
async def yoto_auth_start() -> Dict[str, Any]:
    info = await oauth_device_start()
    # Return the user code and URL to show on the UI
    return {
        "user_code": info.user_code,
        "verification_uri": info.verification_uri,
        "verification_uri_complete": info.verification_uri_complete,
        "device_code": info.device_code,  # UI will POST this back to /poll
        "expires_in": info.expires_in,
        "interval": info.interval,
    }


@app.post("/api/yoto/auth/poll")
async def yoto_auth_poll(payload: Dict[str, Any]) -> Dict[str, Any]:
    device_code = payload.get("device_code")
    if not device_code:
        raise HTTPException(status_code=400, detail="device_code required")

    # Poll once per UI click/timer; UI controls cadence using interval
    try:
        t = await oauth_device_poll(device_code)
        return {
            "authenticated": True,
            "expires_at": t.expires_at,
            "scope": t.scope,
        }
    except RuntimeError as e:
        msg = str(e)
        # bubble up auth-pending in a friendly way
        if "authorization_pending" in msg:
            return {"authenticated": False, "pending": True}
        if "slow_down" in msg:
            return {"authenticated": False, "pending": True, "slow_down": True}
        raise HTTPException(status_code=400, detail=msg)


# -------------------------
# Small Yoto test route (for your 403)
# -------------------------
@app.get("/api/yoto/debug/uploadurl")
async def yoto_debug_uploadurl(sha256: str) -> Dict[str, Any]:
    """
    Call this with any sha256 hex to see if the token is allowed to access uploadUrl.
    """
    try:
        upload_url, upload_id = await request_audio_upload_url(sha256)
        return {"ok": True, "uploadId": upload_id, "uploadUrl": upload_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
