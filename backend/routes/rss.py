from fastapi import APIRouter, HTTPException, Query, Form
from typing import Optional
from services.rss_service import RSSService
from services.yoto_service import YotoService

router = APIRouter()


@router.get("/feeds/parse")
async def parse_feed(feed_url: str = Query(...)):
    """
    Parse an RSS feed and return podcast information and episodes
    """
    try:
        feed_data = RSSService.fetch_feed(feed_url)
        return {
            "success": True,
            "feed": feed_data
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse feed: {str(e)}")


@router.post("/feeds/upload-episode")
async def upload_episode_from_feed(
    audio_url: str = Form(...),
    title: str = Form(...),
    access_token: str = Form(...),
    playlist_card_id: Optional[str] = Form(None),
    chapter_index: int = Form(0)
):
    """
    Download an episode from RSS feed and upload to Yoto
    """
    try:
        # Download audio from RSS feed
        audio_data = RSSService.download_episode(audio_url)
        
        # Upload to Yoto
        yoto = YotoService(access_token)
        result = yoto.upload_podcast_to_playlist(
            audio_file=audio_data,
            podcast_title=title,
            playlist_card_id=playlist_card_id,
            chapter_index=chapter_index,
            track_title=title
        )
        
        return {
            "success": True,
            "message": "Episode uploaded successfully",
            "cardId": result.get("card", {}).get("cardId"),
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )