from fastapi import APIRouter, HTTPException, Query, Form
from typing import Optional
from services.rss_service import RSSService
import hashlib
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
    playlist_name: Optional[str] = Form(None),
    chapter_index: int = Form(0)
):
    """
    Download an episode from RSS feed and upload to Yoto
    """
    try:
        # Download audio from RSS feed
        audio_data = RSSService.download_episode(audio_url)
        # Log debug info about the downloaded audio to help diagnose duplicate uploads
        try:
            audio_hash = hashlib.sha256(audio_data).hexdigest()
            print(f"upload_episode_from_feed: track_title={title} audio_len={len(audio_data)} sha256={audio_hash}")
        except Exception:
            print("upload_episode_from_feed: failed to hash audio data")
        
        # Use playlist_name if provided, otherwise use episode title
        final_playlist_name = playlist_name if playlist_name else title
        
        # Upload to Yoto
        yoto = YotoService(access_token)
        # Log whether we're creating a new playlist or adding to existing
        print(f"upload_episode_from_feed: playlist_card_id={playlist_card_id}, playlist_name={playlist_name}")

        result = yoto.upload_podcast_to_playlist(
            audio_file=audio_data,
            podcast_title=final_playlist_name,
            playlist_card_id=playlist_card_id,
            chapter_index=chapter_index,
            track_title=title
        )
        
        # Log raw result for debugging
        print("upload_episode_from_feed: yoto result:", result)

        # Extract cardId from different possible locations in response
        card_id = None
        if "card" in result:
            card_id = result["card"].get("cardId")
        elif "cardId" in result:
            card_id = result["cardId"]
        
        return {
            "success": True,
            "message": "Episode uploaded successfully",
            "cardId": card_id,
            "playlistId": card_id,  # Also return as playlistId for clarity
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