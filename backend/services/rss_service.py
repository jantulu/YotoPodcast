import feedparser
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime


class RSSService:
    """Service for fetching and parsing RSS podcast feeds"""
    
    @staticmethod
    def fetch_feed(feed_url: str) -> Dict[str, Any]:
        """
        Fetch and parse an RSS feed
        
        Args:
            feed_url: URL of the RSS feed
            
        Returns:
            Parsed feed data
        """
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            raise ValueError(f"Invalid RSS feed: {feed.bozo_exception}")
        
        return {
            "title": feed.feed.get("title", "Unknown Podcast"),
            "description": feed.feed.get("description", ""),
            "link": feed.feed.get("link", ""),
            "image": feed.feed.get("image", {}).get("href", ""),
            "episodes": [
                RSSService._parse_episode(entry)
                for entry in feed.entries
            ]
        }
    
    @staticmethod
    def _parse_episode(entry: Any) -> Dict[str, Any]:
        """Parse a single podcast episode from feed entry"""
        # Get audio URL
        audio_url = None
        audio_type = None
        audio_length = None
        
        # Check enclosures for audio file
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.get('type', '').startswith('audio/'):
                    audio_url = enclosure.get('href')
                    audio_type = enclosure.get('type')
                    audio_length = enclosure.get('length')
                    break
        
        # Fallback to links if no enclosure
        if not audio_url and hasattr(entry, 'links'):
            for link in entry.links:
                if link.get('type', '').startswith('audio/'):
                    audio_url = link.get('href')
                    audio_type = link.get('type')
                    break
        
        # Parse published date
        published = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6]).isoformat()
        
        return {
            "title": entry.get("title", "Unknown Episode"),
            "description": entry.get("summary", ""),
            "audio_url": audio_url,
            "audio_type": audio_type,
            "audio_length": audio_length,
            "published": published,
            "duration": entry.get("itunes_duration", ""),
            "guid": entry.get("id", entry.get("link", ""))
        }
    
    @staticmethod
    def download_episode(audio_url: str) -> bytes:
        """
        Download an audio file from URL
        
        Args:
            audio_url: URL of the audio file
            
        Returns:
            Audio file bytes
        """
        response = requests.get(audio_url, stream=True, timeout=300)
        response.raise_for_status()
        
        # Read in chunks to handle large files
        audio_data = b""
        for chunk in response.iter_content(chunk_size=8192):
            audio_data += chunk
        
        return audio_data