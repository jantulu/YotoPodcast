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
            f"{self.BASE_URL}/content/myo",
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
            return response.json()
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
        
        chapters = playlist.get("content", {}).get("chapters", [])
        
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
        
        # Update track key based on existing tracks
        existing_tracks = chapters[chapter_index].get("tracks", [])
        new_track_num = len(existing_tracks) + 1
        new_track["key"] = f"{new_track_num:02d}"
        new_track["overlayLabel"] = str(new_track_num)
        
        # Add track to chapter
        chapters[chapter_index]["tracks"].append(new_track)
        
        # Update the playlist
        return self.update_existing_playlist(
            card_id=card_id,
            title=playlist.get("title", ""),
            chapters=chapters,
            metadata=playlist.get("metadata")
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
            podcast_title: Title for the podcast/track
            playlist_card_id: If provided, adds to existing playlist. If None, creates new.
            chapter_index: Which chapter to add the track to (0-indexed)
            track_title: Title for the individual track (defaults to podcast_title)
        
        Returns:
            The updated or created playlist data with cardId
        """
        track_title = track_title or podcast_title
        
        # Step 1: Get upload URL
        upload_info = self.get_upload_url()
        
        # Step 2: Upload audio file
        self.upload_audio_file(upload_info["uploadUrl"], audio_file)
        
        # Step 3: Wait for transcoding
        transcoded_data = self.wait_for_transcoding(upload_info["uploadId"])
        
        # Step 4: Create track object
        track = self.create_track_from_transcode(
            transcoded_data,
            track_key="01",
            title=track_title
        )
        
        # Step 5: Either update existing playlist or create new one
        if playlist_card_id:
            result = self.add_track_to_playlist(playlist_card_id, chapter_index, track)
        else:
            chapter = {
                "key": "01",
                "title": podcast_title,
                "overlayLabel": "1",
                "tracks": [track],
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
        
        return result