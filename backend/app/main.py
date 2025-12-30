from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import podcasts
from .yoto import auth_start, auth_status, upload_episode_audio

app = FastAPI(title="Podcast → Yoto Uploader")

# CORS REQUIRED
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local LAN + dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UploadRequest(BaseModel):
    audioUrl: str
    title: str


@app.get("/api/health")
async def health():
    return {"ok": True}


@app.post("/api/yoto/auth/start")
async def yoto_auth_start():
    return await auth_start()


@app.get("/api/yoto/auth/status")
async def yoto_auth_status():
    return await auth_status()


@app.get("/api/podcasts")
async def get_podcasts():
    return await podcasts.list_podcasts()


@app.get("/api/podcasts/{slug}/episodes")
async def get_episodes(slug: str):
    eps = await podcasts.list_episodes(slug)
    if not eps:
        raise HTTPException(status_code=404, detail="No episodes found")
    return eps


@app.post("/api/yoto/upload")
async def yoto_upload(req: UploadRequest):
    try:
        return await upload_episode_audio(req.audioUrl, req.title)
    except RuntimeError as e:
        # auth missing etc.
        raise HTTPException(status_code=400, detail=str(e))
