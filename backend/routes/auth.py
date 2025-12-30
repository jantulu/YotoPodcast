from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import requests
from config import settings
from models.schemas import TokenResponse

router = APIRouter()


@router.get("/authorize")
async def get_authorize_url(redirect_uri: Optional[str] = None):
    """Generate the OAuth authorization URL"""
    redirect = redirect_uri or settings.YOTO_REDIRECT_URI
    
    auth_url = (
        f"{settings.YOTO_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={settings.YOTO_CLIENT_ID}"
        f"&redirect_uri={redirect}"
        f"&scope=library.read library.write"
    )
    
    return {"authorization_url": auth_url}


@router.post("/token")
async def exchange_token(code: str = Query(...), redirect_uri: Optional[str] = None):
    """Exchange authorization code for access token"""
    redirect = redirect_uri or settings.YOTO_REDIRECT_URI
    
    try:
        response = requests.post(
            settings.YOTO_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect,
                "client_id": settings.YOTO_CLIENT_ID,
                "client_secret": settings.YOTO_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        response.raise_for_status()
        token_data = response.json()
        
        return TokenResponse(**token_data)
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=f"Token exchange failed: {str(e)}"
        )


@router.post("/refresh")
async def refresh_token(refresh_token: str = Query(...)):
    """Refresh an expired access token"""
    try:
        response = requests.post(
            settings.YOTO_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.YOTO_CLIENT_ID,
                "client_secret": settings.YOTO_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        response.raise_for_status()
        token_data = response.json()
        
        return TokenResponse(**token_data)
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=f"Token refresh failed: {str(e)}"
        )