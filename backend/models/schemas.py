from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class TokenResponse(BaseModel):
    """OAuth token response"""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None


class DeviceCodeResponse(BaseModel):
    """Device code flow response"""
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int = 5


class PlaylistInfo(BaseModel):
    """Basic playlist information"""
    cardId: str
    title: str
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class UploadRequest(BaseModel):
    """Request model for uploading podcasts"""
    title: str
    playlist_card_id: Optional[str] = None
    chapter_index: int = 0


class UploadResponse(BaseModel):
    """Response model for upload operations"""
    success: bool
    message: str
    cardId: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class PlaylistListResponse(BaseModel):
    """Response model for playlist list"""
    success: bool
    playlists: List[PlaylistInfo]