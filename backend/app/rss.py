import feedparser
import httpx

async def fetch_rss(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text

def parse_episodes(rss_text: str) -> list[dict]:
    feed = feedparser.parse(rss_text)
    episodes: list[dict] = []

    for entry in feed.entries:
        enclosure_url = None
        mime_type = None

        # Standard podcast feeds usually expose enclosure in links
        for link in getattr(entry, "links", []) or []:
            if link.get("rel") == "enclosure" and link.get("href"):
                enclosure_url = link.get("href")
                mime_type = link.get("type")
                break

        guid = getattr(entry, "id", None) or getattr(entry, "guid", None) or enclosure_url or entry.get("title", "")
        episodes.append({
            "guid": str(guid),
            "title": entry.get("title", "Untitled"),
            "published": entry.get("published", ""),
            "enclosureUrl": enclosure_url,
            "mimeType": mime_type,
        })

    # Keep only items with audio enclosure
    episodes = [e for e in episodes if e["enclosureUrl"]]
    return episodes
