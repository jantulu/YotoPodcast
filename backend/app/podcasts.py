from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import feedparser
import httpx


PODCASTS = [
    {"slug": "99pi", "title": "99% Invisible", "feedUrl": "https://feeds.99percentinvisible.org/99percentinvisible"},
    {"slug": "circle-round", "title": "Circle Round", "feedUrl": "https://feeds.npr.org/510313/podcast.xml"},
]

# If you want to keep "circle-round has no episodes", set its feedUrl to "" or use STUB_ONLY map below.


STUB_EPISODES: dict[str, list[dict[str, Any]]] = {
    "99pi": [
        {"id": "ep1", "title": "Example Episode", "audioUrl": "https://example.com/audio.mp3"}
    ],
    # "circle-round": []  # intentionally empty -> will 404 in API if slug exists but no episodes
}

STUB_ONLY = True  # flip to False to enable RSS parsing


@dataclass
class Episode:
    id: str
    title: str
    audioUrl: str


async def list_podcasts() -> list[dict[str, Any]]:
    return PODCASTS


async def list_episodes(slug: str) -> list[dict[str, Any]]:
    if STUB_ONLY:
        episodes = STUB_EPISODES.get(slug)
        if not episodes:
            # keep your current behavior: 404 when no episodes
            return []
        return episodes

    pod = next((p for p in PODCASTS if p["slug"] == slug), None)
    if not pod or not pod.get("feedUrl"):
        return []

    feed_url = pod["feedUrl"]
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(feed_url)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)

    out: list[dict[str, Any]] = []
    for entry in parsed.entries[:50]:
        title = entry.get("title", "Untitled Episode")
        # best-effort audio enclosure
        audio_url = None
        for link in entry.get("links", []):
            if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("audio/"):
                audio_url = link.get("href")
                break
        if not audio_url:
            continue

        ep_id = entry.get("id") or entry.get("guid") or audio_url
        out.append({"id": str(ep_id), "title": str(title), "audioUrl": str(audio_url)})

    return out
