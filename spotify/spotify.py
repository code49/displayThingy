import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def get_spotify_client():
    """
    Initializes and returns a Spotify client using credentials from .env
    """
    load_dotenv()
    
    scope = "user-read-playback-state user-read-currently-playing"
    
    auth_manager = SpotifyOAuth(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
        scope=scope,
        cache_path=".spotify_cache",
        open_browser=True
    )
    
    return spotipy.Spotify(auth_manager=auth_manager)

def get_current_track_info(sp):
    """
    Fetches information about the currently playing song or podcast episode.
    Returns a dictionary with details or None if nothing is playing.
    """
    try:
        # Include 'episode' in additional_types for podcast support
        playback = sp.current_playback(additional_types=['track', 'episode'])
        
        if playback is None or playback['item'] is None:
            return None
            
        item = playback['item']
        item_type = item.get('type')
        
        if item_type == 'episode':
            # Podcast Episode
            track_info = {
                'name': item['name'],
                'artist': item['show']['publisher'],
                'album': item['show']['name'],
                'cover_url': item['show']['images'][0]['url'] if item['show']['images'] else None,
                'duration_ms': item['duration_ms'],
                'progress_ms': playback['progress_ms'],
                'is_playing': playback['is_playing'],
                'type': 'podcast'
            }
        else:
            # Music Track
            track_info = {
                'name': item['name'],
                'artist': ", ".join([artist['name'] for artist in item['artists']]),
                'album': item['album']['name'],
                'cover_url': item['album']['images'][0]['url'] if item['album']['images'] else None,
                'duration_ms': item['duration_ms'],
                'progress_ms': playback['progress_ms'],
                'is_playing': playback['is_playing'],
                'type': 'track'
            }
        
        return track_info
    except Exception as e:
        print(f"Error fetching Spotify data: {e}")
        return None

import time

def get_interpolated_progress(track_info, last_sync_time):
    """
    Calculates the estimated current progress in ms based on elapsed time 
    since the last API sync.
    """
    if not track_info:
        return 0
        
    if not track_info['is_playing']:
        return track_info['progress_ms']
        
    elapsed_ms = (time.time() - last_sync_time) * 1000
    interpolated_ms = track_info['progress_ms'] + elapsed_ms
    
    # Cap at song duration
    return min(interpolated_ms, track_info['duration_ms'])
