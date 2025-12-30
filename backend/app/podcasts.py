import json
from pathlib import Path
from .settings import settings

def load_podcasts() -> list[dict]:
    p = Path(settings.podcasts_file)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))
