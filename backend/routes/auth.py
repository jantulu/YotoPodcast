from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import requests
from config import settings
from models.schemas import TokenResponse, DeviceCodeResponse

router = APIRouter()


@router.post("/device/code")
async def initiate_device_flow():
    """
    Initiate device authorization flow.
    Returns device_code and user_code for the user to authorize.
    """
    try:
        print(f"Initiating device flow with client_id: {settings.YOTO_CLIENT_ID}")
        
        response = requests.post(
            "https://login.yotoplay.com/oauth/device/code",
            data={
                "client_id": settings.YOTO_CLIENT_ID,
                "scope": "profile offline_access",
                "audience": "https://api.yotoplay.com"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"Device code response status: {response.status_code}")
        print(f"Device code response body: {response.text}")
        
        if not response.ok:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("error_description", error_json.get("error", response.text))
            except:
                pass
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Device code request failed: {error_detail}"
            )
        
        data = response.json()
        
        return DeviceCodeResponse(
            device_code=data["device_code"],
            user_code=data["user_code"],
            verification_uri=data.get("verification_uri_complete", data["verification_uri"]),
            expires_in=data.get("expires_in", 300),
            interval=data.get("interval", 5)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Device flow error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Device code request failed: {str(e)}"
        )


@router.post("/device/token")
async def poll_device_token(device_code: str = Query(...)):
    """
    Poll for access token after user has authorized the device.
    This should be called repeatedly until token is returned or error occurs.
    """
    try:
        response = requests.post(
            "https://login.yotoplay.com/oauth/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
                "client_id": settings.YOTO_CLIENT_ID,
                "audience": "https://api.yotoplay.com"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Handle pending authorization
        if response.status_code == 403:
            error_data = response.json()
            error_code = error_data.get("error")
            
            if error_code == "authorization_pending":
                raise HTTPException(
                    status_code=202,
                    detail="Authorization pending"
                )
            elif error_code == "slow_down":
                raise HTTPException(
                    status_code=202,
                    detail="Slow down - increase polling interval"
                )
            elif error_code == "expired_token":
                raise HTTPException(
                    status_code=400,
                    detail="Device code expired"
                )
            elif error_code == "access_denied":
                raise HTTPException(
                    status_code=403,
                    detail="User denied authorization"
                )
        
        response.raise_for_status()
        token_data = response.json()
        
        return TokenResponse(**token_data)
        
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=f"Token poll failed: {str(e)}"
        )


@router.post("/refresh")
async def refresh_token(refresh_token: str = Query(...)):
    """Refresh an expired access token"""
    try:
        response = requests.post(
            "https://login.yotoplay.com/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": settings.YOTO_CLIENT_ID,
                "refresh_token": refresh_token,
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