import time
import requests
from typing import Optional, Dict, Any, List


class YotoService:
    BASE_URL = "https://api.yotoplay.com"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def get_user_playlists(self) -> List[Dict[str, Any]]:
        """Fetch all user's MYO playlists"""
        response = requests.get(
            f"{self.BASE_URL}/content/mine",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json().get("cards", [])
    
    def get_playlist_by_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific playlist by cardId"""
        response = requests.get(
            f"{self.BASE_URL}/content/{card_id}",
            headers=self.headers
        )
        if response.status_code == 200:
            data = response.json()
            print(f"get_playlist_by_id response structure: {list(data.keys())}")
            # The API returns {"card": {...}} so we need to return the whole thing
            return data
        return None
    
    def delete_playlist(self, card_id: str) -> bool:
        """Delete a playlist by cardId"""
        response = requests.delete(
            f"{self.BASE_URL}/content/{card_id}",
            headers=self.headers
        )
        return response.status_code == 200
    
    def get_upload_url(self) -> Dict[str, str]:
        """Request a signed upload URL for audio"""
        response = requests.get(
            f"{self.BASE_URL}/media/transcode/audio/uploadUrl",
            headers=self.headers
        )
        response.raise_for_status()
        data = response.json()
        return {
            "uploadUrl": data["upload"]["uploadUrl"],
            "uploadId": data["upload"]["uploadId"]
        }
    
    def upload_audio_file(self, upload_url: str, audio_file: bytes, content_type: str = "audio/mpeg"):
        """Upload audio file to the signed URL"""
        response = requests.put(
            upload_url,
            data=audio_file,
            headers={"Content-Type": content_type}
        )
        response.raise_for_status()
    
    def wait_for_transcoding(self, upload_id: str, max_attempts: int = 60, delay: float = 1.0) -> Dict[str, Any]:
        """Poll the API until transcoding is complete"""
        for attempt in range(max_attempts):
            response = requests.get(
                f"{self.BASE_URL}/media/upload/{upload_id}/transcoded?loudnorm=false",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("transcode", {}).get("transcodedSha256"):
                    return data["transcode"]
            
            time.sleep(delay)
        
        raise TimeoutError(f"Transcoding timed out after {max_attempts} attempts")
    
    def create_track_from_transcode(
        self, 
        transcoded_data: Dict[str, Any], 
        track_key: str, 
        title: str
    ) -> Dict[str, Any]:
        """Create a track object from transcoded audio data"""
        media_info = transcoded_data.get("transcodedInfo", {})
        
        return {
            "key": track_key,
            "title": title,
            "trackUrl": f"yoto:#{transcoded_data['transcodedSha256']}",
            "duration": media_info.get("duration"),
            "fileSize": media_info.get("fileSize"),
            "channels": media_info.get("channels"),
            "format": media_info.get("format"),
            "type": "audio",
            "overlayLabel": track_key,
            "display": {
                "icon16x16": "yoto:#aUm9i3ex3qqAMYBv-i-O-pYMKuMJGICtR3Vhf289u2Q"
            }
        }
    
    def create_new_playlist(
        self, 
        title: str, 
        chapters: List[Dict[str, Any]], 
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a new playlist"""
        content = {
            "title": title,
            "content": {
                "chapters": chapters,
                "config": {
                    "resumeTimeout": 2592000
                },
                "playbackType": "linear"
            }
        }
        
        if metadata:
            content["metadata"] = metadata
        
        response = requests.post(
            f"{self.BASE_URL}/content",
            headers=self.headers,
            json=content
        )
        response.raise_for_status()
        return response.json()
    
    def update_existing_playlist(
        self, 
        card_id: str, 
        title: str, 
        chapters: List[Dict[str, Any]], 
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Update an existing playlist by cardId"""
        content = {
            "cardId": card_id,  # CRITICAL: This makes it an update instead of create
            "title": title,
            "content": {
                "chapters": chapters,
                "config": {
                    "resumeTimeout": 2592000
                },
                "playbackType": "linear"
            }
        }
        
        if metadata:
            content["metadata"] = metadata
        
        response = requests.post(
            f"{self.BASE_URL}/content",
            headers=self.headers,
            json=content
        )
        response.raise_for_status()
        return response.json()
    
    def add_track_to_playlist(
        self, 
        card_id: str, 
        chapter_index: int, 
        new_track: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a new track to an existing chapter in a playlist"""
        playlist = self.get_playlist_by_id(card_id)
        if not playlist:
            raise ValueError(f"Playlist with cardId {card_id} not found")
        
        # Get the card content, not the wrapper
        card_data = playlist.get("card", playlist)
        chapters = card_data.get("content", {}).get("chapters", [])
        
        print(f"Current playlist has {len(chapters)} chapter(s)")
        if len(chapters) > 0:
            print(f"Chapter 0 has {len(chapters[0].get('tracks', []))} track(s)")
        
        # Ensure chapter exists
        if chapter_index >= len(chapters):
            for i in range(len(chapters), chapter_index + 1):
                chapters.append({
                    "key": f"{i+1:02d}",
                    "title": f"Chapter {i+1}",
                    "overlayLabel": str(i+1),
                    "tracks": [],
                    "display": {
                        "icon16x16": "yoto:#aUm9i3ex3qqAMYBv-i-O-pYMKuMJGICtR3Vhf289u2Q"
                    }
                })
        
        # CRITICAL: Get existing tracks from the correct chapter
        existing_tracks = chapters[chapter_index].get("tracks", [])
        new_track_num = len(existing_tracks) + 1
        
        print(f"Existing tracks in chapter {chapter_index}: {len(existing_tracks)}")
        print(f"New track will be #{new_track_num}")
        
        # Create NEW dict with updated key
        track_to_add = {
            **new_track,
            "key": f"{new_track_num:02d}",
            "overlayLabel": str(new_track_num)
        }
        
        print(f"Adding track #{new_track_num} with key '{track_to_add['key']}' to playlist {card_id}")
        print(f"Track title: {track_to_add.get('title')}")
        print(f"Track URL: {track_to_add.get('trackUrl', 'N/A')[:50]}...")
        
        # Add track to chapter
        chapters[chapter_index]["tracks"].append(track_to_add)
        
        # Get the correct title and metadata from the card
        playlist_title = card_data.get("title", "")
        playlist_metadata = card_data.get("metadata")
        
        # Update the playlist
        return self.update_existing_playlist(
            card_id=card_id,
            title=playlist_title,
            chapters=chapters,
            metadata=playlist_metadata
        )
    
    def upload_podcast_to_playlist(
        self,
        audio_file: bytes,
        podcast_title: str,
        playlist_card_id: Optional[str] = None,
        chapter_index: int = 0,
        track_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete workflow to upload a podcast episode to a playlist.
        
        Args:
            audio_file: The audio file bytes
            podcast_title: Title for the podcast/playlist
            playlist_card_id: If provided, adds to existing playlist. If None, creates new.
            chapter_index: Which chapter to add the track to (0-indexed)
            track_title: Title for the individual track (defaults to podcast_title)
        
        Returns:
            The updated or created playlist data with cardId
        """
        track_title = track_title or podcast_title
        
        print(f"\n=== Starting upload for track: {track_title} ===")
        print(f"Playlist title: {podcast_title}")
        print(f"Target playlist ID: {playlist_card_id}")
        
        # Step 1: Get upload URL
        upload_info = self.get_upload_url()
        print(f"Got upload URL: {upload_info['uploadId']}")
        
        # Step 2: Upload audio file
        self.upload_audio_file(upload_info["uploadUrl"], audio_file)
        print("Audio uploaded, waiting for transcoding...")
        
        # Step 3: Wait for transcoding
        transcoded_data = self.wait_for_transcoding(upload_info["uploadId"])
        print(f"Transcoding complete: {transcoded_data['transcodedSha256'][:10]}...")
        
        # Step 4: Create track object - DON'T set key yet, it will be set when adding to playlist
        track = self.create_track_from_transcode(
            transcoded_data,
            track_key="PLACEHOLDER",  # Will be replaced when adding to playlist
            title=track_title
        )
        
        # Step 5: Either update existing playlist or create new one
        if playlist_card_id:
            print(f"Adding track to existing playlist: {playlist_card_id}")
            result = self.add_track_to_playlist(playlist_card_id, chapter_index, track)
        else:
            print(f"Creating new playlist: {podcast_title}")
            chapter = {
                "key": "01",
                "title": podcast_title,
                "overlayLabel": "1",
                "tracks": [{
                    **track,
                    "key": "01",  # First track in new playlist
                    "overlayLabel": "1"
                }],
                "display": {
                    "icon16x16": "yoto:#aUm9i3ex3qqAMYBv-i-O-pYMKuMJGICtR3Vhf289u2Q"
                }
            }
            
            media_info = transcoded_data.get("transcodedInfo", {})
            metadata = {
                "media": {
                    "duration": media_info.get("duration"),
                    "fileSize": media_info.get("fileSize"),
                    "readableFileSize": round((media_info.get("fileSize", 0) / 1024 / 1024) * 10) / 10
                }
            }
            
            result = self.create_new_playlist(
                title=podcast_title,
                chapters=[chapter],
                metadata=metadata
            )
        
        # Ensure cardId is at top level of response
        if "card" in result and "cardId" in result["card"]:
            result["cardId"] = result["card"]["cardId"]

        # Verification: confirm the created trackUrl appears in the playlist returned by the API
        try:
            result_card_id = result.get("cardId") or (result.get("card") or {}).get("cardId")
            verified = False
            if result_card_id:
                fetched = self.get_playlist_by_id(result_card_id)
                # fetched may be wrapped under 'card'
                card_obj = fetched.get("card") if isinstance(fetched, dict) and "card" in fetched else fetched
                chapters = (card_obj or {}).get("content", {}).get("chapters", [])
                for ch in chapters:
                    for t in ch.get("tracks", []) or []:
                        if t.get("trackUrl") == track.get("trackUrl"):
                            verified = True
                            break
                    if verified:
                        break
            result["verified"] = verified
            if verified:
                print(f"upload_podcast_to_playlist: verification OK for cardId={result_card_id}")
            else:
                print(f"upload_podcast_to_playlist: verification FAILED for cardId={result_card_id} trackUrl={track.get('trackUrl')}")
        except Exception as e:
            print("upload_podcast_to_playlist: verification error:", str(e))

        print(f"Upload complete! CardID: {result.get('cardId')}")
        print("=" * 50)

        return result