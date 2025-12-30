from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from services.yoto_service import YotoService
from models.schemas import UploadResponse

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_podcast(
    audio: UploadFile = File(...),
    title: str = Form(...),
    access_token: str = Form(...),
    playlist_card_id: Optional[str] = Form(None),
    chapter_index: int = Form(0)
):
    """
    Upload a podcast episode to Yoto.
    
    - If playlist_card_id is provided: adds to existing playlist
    - If playlist_card_id is None: creates a new playlist
    """
    try:
        # Validate file type
        if not audio.content_type or not audio.content_type.startswith('audio/'):
            raise HTTPException(
                status_code=400,
                detail="File must be an audio file"
            )
        
        # Read audio file
        audio_content = await audio.read()
        
        if len(audio_content) == 0:
            raise HTTPException(
                status_code=400,
                detail="Audio file is empty"
            )
        
        # Initialize Yoto service
        yoto = YotoService(access_token)
        
        # Upload podcast
        result = yoto.upload_podcast_to_playlist(
            audio_file=audio_content,
            podcast_title=title,
            playlist_card_id=playlist_card_id,
            chapter_index=chapter_index,
            track_title=title
        )
        
        card_id = result.get("card", {}).get("cardId")
        
        return UploadResponse(
            success=True,
            message="Podcast uploaded successfully",
            cardId=card_id,
            data=result
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )