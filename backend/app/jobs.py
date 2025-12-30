# backend/app/jobs.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class JobState:
    status: str = "queued"        # queued | running | done | error
    message: str = ""
    current: int = 0              # 1-based episode index
    total: int = 0
    phase: str = ""               # download | upload | transcode | content
    episode_title: str = ""
    result: Any = None
    error: str | None = None
    updated_at: float = field(default_factory=time.time)


JOBS: dict[str, JobState] = {}
