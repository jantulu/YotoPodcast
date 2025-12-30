from fastapi import APIRouter, HTTPException, Query
from services.yoto_service import YotoService
from models.schemas import PlaylistListResponse, PlaylistInfo

router = APIRouter()


@router.get("", response_model=PlaylistListResponse)
async def get_playlists(access_token: str = Query(...)):
    """Get all user's MYO playlists"""
    try:
        yoto = YotoService(access_token)
        playlists = yoto.get_user_playlists()
        
        playlist_infos = [
            PlaylistInfo(
                cardId=p.get("cardId", ""),
                title=p.get("title", "Untitled"),
                createdAt=p.get("createdAt"),
                updatedAt=p.get("updatedAt")
            )
            for p in playlists
        ]
        
        return PlaylistListResponse(
            success=True,
            playlists=playlist_infos
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{card_id}")
async def get_playlist(card_id: str, access_token: str = Query(...)):
    """Get a specific playlist by cardId"""
    try:
        yoto = YotoService(access_token)
        playlist = yoto.get_playlist_by_id(card_id)
        
        if not playlist:
            raise HTTPException(
                status_code=404,
                detail="Playlist not found"
            )
        
        return {"success": True, "playlist": playlist}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{card_id}")
async def delete_playlist(card_id: str, access_token: str = Query(...)):
    """Delete a playlist by cardId"""
    try:
        yoto = YotoService(access_token)
        success = yoto.delete_playlist(card_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Playlist not found or already deleted"
            )
        
        return {
            "success": True,
            "message": "Playlist deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))