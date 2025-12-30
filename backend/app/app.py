import os
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .yoto import (
    upload_audio_to_yoto,
    TranscodedResult,
    oauth_device_start,
    oauth_device_poll,
    yoto_healthcheck,
)

logger = logging.getLogger("podcast-yoto")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


def _parse_origins() -> list[str]:
    """
    CORS_ORIGINS="http://localhost:5173,http://10.1.27.19:5173"
    If you are using the Vite proxy (recommended), you can set this to just localhost
    or even skip it, but it's safe to keep.
    """
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins


app = FastAPI(title="podcast-yoto-backend")

# --- CORS FIX ---
# If you're using the Vite proxy, CORS is largely irrelevant, but leaving this on makes direct calls work too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------
# Models
# ----------------------------
class AuthStartResponse(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: Optional[str] = None
    expires_in: int
    interval: int


class AuthPollRequest(BaseModel):
    device_code: str


class UploadRequest(BaseModel):
    # path to local file on server container (e.g. /data/tmp/foo.bin)
    file_path: str
    # optional mime override (audio/mpeg etc)
    mime_type: Optional[str] = None


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    ok = await yoto_healthcheck()
    return {"ok": ok}


@app.post("/api/yoto/auth/start", response_model=AuthStartResponse)
async def yoto_auth_start() -> AuthStartResponse:
    """
    Starts the Yoto OAuth device/code flow (web-code style).
    Your frontend should display user_code + verification_uri_complete (if present).
    """
    try:
        info = await oauth_device_start()
        return AuthStartResponse(**info)
    except Exception as e:
        logger.exception("yoto_auth_start failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/yoto/auth/poll")
async def yoto_auth_poll(req: AuthPollRequest) -> Dict[str, Any]:
    """
    Polls the device code until authorized or expired.
    Returns tokens when ready.
    """
    try:
        return await oauth_device_poll(req.device_code)
    except Exception as e:
        logger.exception("yoto_auth_poll failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/yoto/upload")
async def yoto_upload(req: UploadRequest) -> Dict[str, Any]:
    """
    Uploads a local file path to Yoto media upload/transcode.
    (Playlist/content creation may still be restricted based on token roles.)
    """
    job_id = str(uuid.uuid4())
    logger.info("JOB %s: upload request file=%s", job_id, req.file_path)

    try:
        trans: TranscodedResult = await upload_audio_to_yoto(
            req.file_path, mime_type=req.mime_type
        )
        logger.info("JOB %s: upload done uploadId=%s sha=%s", job_id, trans.upload_id, trans.sha)
        return {
            "jobId": job_id,
            "uploadId": trans.upload_id,
            "sha": trans.sha,
            "trackUrl": f"yoto:#{trans.sha}",
            "raw": trans.raw,
        }
    except Exception as e:
        logger.exception("JOB %s: upload failed", job_id)
        raise HTTPException(status_code=500, detail=str(e))
