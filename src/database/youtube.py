"""
YouTube API integration for song recommendation system.
This module handles fetching song data from YouTube.
"""

import os
import googleapiclient.discovery
from googleapiclient.errors import HttpError
import logging
from dotenv import load_dotenv
from ytmusicapi import YTMusic

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get YouTube API key
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    logger.error("YouTube API key not found in environment variables.")
    raise ValueError("YouTube API key is required. Please set YOUTUBE_API_KEY in your .env file.")

# Initialize YouTube Music API
ytmusic = YTMusic(language="zh_TW", location="SG")

def get_youtube_client():
    """
    Create and return a YouTube API client.
    
    Returns:
        googleapiclient.discovery.Resource: YouTube API client
    """
    try:
        youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=YOUTUBE_API_KEY
        )
        return youtube
    except Exception as e:
        logger.error(f"Error creating YouTube client: {e}")
        raise

def search_song(query, max_results=1):
    """
    Search for a song on YouTube.
    
    Args:
        query (str): Search query (song name + artist)
        max_results (int, optional): Maximum number of results to return. Defaults to 1.
    
    Returns:
        list: List of dictionaries with song information
    """
    youtube = get_youtube_client()
    
    try:
        # Search for the song
        search_response = youtube.search().list(
            q=query,
            part="id,snippet",
            maxResults=max_results,
            type="video",
            videoCategoryId="10",  # Music category
            fields="items(id(videoId),snippet(title,channelTitle,publishedAt,thumbnails))"
        ).execute()
        
        results = []
        for item in search_response.get("items", []):
            if "videoId" in item.get("id", {}):
                video_id = item["id"]["videoId"]
                
                # Get video details
                video_response = youtube.videos().list(
                    part="contentDetails,statistics",
                    id=video_id
                ).execute()
                
                video_details = video_response.get("items", [])[0] if video_response.get("items") else {}
                content_details = video_details.get("contentDetails", {})
                statistics = video_details.get("statistics", {})
                
                results.append({
                    "video_id": video_id,
                    "title": item["snippet"]["title"],
                    "channel_title": item["snippet"]["channelTitle"],
                    "published_at": item["snippet"]["publishedAt"],
                    # "duration": content_details.get("duration", ""),
                    "view_count": int(statistics.get("viewCount", 0)),
                    "like_count": int(statistics.get("likeCount", 0)),
                    "thumbnail": item["snippet"]["thumbnails"]["high"]["url"] if "high" in item["snippet"]["thumbnails"] else ""
                })
        
        return results
    
    except HttpError as e:
        logger.error(f"YouTube API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error searching for song: {e}")
        raise

def get_popular_music_videos(max_results=50, region_code="SG", language="zh_TW"):
    """
    Get the most popular music videos on YouTube.
    
    Args:
        max_results (int, optional): Maximum number of results to return. Defaults to 10.
        region_code (str, optional): Region code for localized results. Defaults to "SG".
        language (str, optional): Language code for results. Defaults to "zh_TW" for Traditional Chinese.
    
    Returns:
        list: List of dictionaries with song information
    """
    try:
        # Get popular Chinese songs from YouTube Music
        search_results = ytmusic.search(
            query="华语音乐 流行歌曲",
            filter="songs",
            limit=max_results
        )
        
        results = []
        for item in search_results[:max_results]:
            if item.get('videoId'):
                video_id = item['videoId']
                
                # Get video details from YouTube Data API
                youtube = get_youtube_client()
                video_response = youtube.videos().list(
                    part="snippet,statistics",
                    id=video_id
                ).execute()
                
                video_details = video_response.get("items", [])[0] if video_response.get("items") else {}
                snippet = video_details.get("snippet", {})
                statistics = video_details.get("statistics", {})
                
                # Extract artist and title from YouTube Music metadata
                artist_name = item.get('artists', [{}])[0].get('name', '')
                song_title = item.get('title', '')
                
                # If YouTube Music metadata is not available, fall back to video title
                if not artist_name or not song_title:
                    artist_name = snippet.get("channelTitle", "")
                    song_title = snippet.get("title", "")
                
                results.append({
                    "videoId": video_id,
                    "title": song_title.split('(')[0].strip(),
                    "channelTitle": artist_name,  # Using artist name as channel title
                    "publishedAt": snippet.get("publishedAt", ""),
                    "viewCount": int(statistics.get("viewCount", 0)),
                    "likeCount": int(statistics.get("likeCount", 0))
                })
        
        return results
    
    except Exception as e:
        logger.error(f"Error getting popular music videos: {e}")
        raise