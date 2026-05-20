import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def get_spotify_client():
    """
    Initializes and returns a Spotify client using credentials from .env
    """
    load_dotenv()
    
    scope = "user-read-playback-state user-read-currently-playing user-read-playback-position"
    
    auth_manager = SpotifyOAuth(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
        scope=scope,
        cache_path=".spotify_cache",
        open_browser=True,
        requests_timeout=10
    )
    
    return spotipy.Spotify(auth_manager=auth_manager, requests_timeout=10)

def get_current_track_info(sp, debug=False):
    """
    Fetches information about the currently playing song or podcast episode.
    Returns a dictionary with details or None if nothing is playing.
    """
    try:
        # 1. Get Playback State
        playback = sp.current_playback(additional_types=['track', 'episode'], market='from_token')
        if debug:
            print(f"DEBUG: current_playback item present: {playback.get('item') is not None if playback else 'None'}")
        
        # 2. Fallback to currently_playing if needed
        if playback is None or playback.get('item') is None:
            if debug: print("DEBUG: playback/item is None, trying currently_playing...")
            temp_playback = sp.currently_playing(additional_types=['track', 'episode'], market='from_token')
            if temp_playback:
                if debug: print(f"DEBUG: currently_playing item present: {temp_playback.get('item') is not None}")
                playback = temp_playback

        if playback is None:
            if debug: print("DEBUG: Final playback object is None")
            return None

        # 3. Resolve the Item (Track or Episode)
        item = playback.get('item')
        if debug: print(f"DEBUG: currently_playing_type: {playback.get('currently_playing_type')}")
        
        # Special handling for podcasts when item is None but type is 'episode'
        if item is None and playback.get('currently_playing_type') == 'episode':
            if debug: print(f"DEBUG: Full playback dump for episode: {playback}")
            
            # Fallback 1: Check Context
            context = playback.get('context')
            if context and context.get('type') == 'episode':
                episode_id = context.get('uri', '').split(':')[-1]
                if debug: print(f"DEBUG: Attempting direct fetch for episode_id: {episode_id}")
                try:
                    item = sp.episode(episode_id)
                    if debug: print(f"DEBUG: Direct fetch success: {item is not None}")
                except: pass

            # Fallback 2: Check Queue (Often contains the current item)
            if item is None:
                if debug: print("DEBUG: Item still None, checking queue...")
                try:
                    queue = sp.queue()
                    if queue and queue.get('currently_playing'):
                        item = queue['currently_playing']
                        if debug: print(f"DEBUG: Found item in queue: {item.get('name')}")
                except Exception as e:
                    if debug: print(f"DEBUG: Queue check failed: {e}")

        if item is None:
            if debug: print("DEBUG: Final item is None")
            return None
            
        item_type = item.get('type') or playback.get('currently_playing_type')
        if debug: print(f"DEBUG: Resolved item_type: {item_type}")
        
        if item_type == 'episode':
            # Podcast Episode
            show = item.get('show', {})
            track_info = {
                'name': item.get('name', 'Unknown Episode'),
                'artist': show.get('publisher', 'Unknown Publisher'),
                'album': show.get('name', 'Unknown Show'),
                'cover_url': (item.get('images', [{}])[0].get('url') or 
                             show.get('images', [{}])[0].get('url')) if (item.get('images') or show.get('images')) else None,
                'duration_ms': item.get('duration_ms', 0),
                'progress_ms': playback.get('progress_ms', 0),
                'is_playing': playback.get('is_playing', False),
                'type': 'podcast'
            }
        else:
            # Music Track
            album = item.get('album', {})
            track_info = {
                'name': item.get('name', 'Unknown Track'),
                'artist': ", ".join([artist['name'] for artist in item.get('artists', [])]) or "Unknown Artist",
                'album': album.get('name', 'Unknown Album'),
                'cover_url': album.get('images', [{}])[0].get('url') if album.get('images') else None,
                'duration_ms': item.get('duration_ms', 0),
                'progress_ms': playback.get('progress_ms', 0),
                'is_playing': playback.get('is_playing', False),
                'type': 'track'
            }
        
        return track_info
    except Exception as e:
        print(f"Error fetching Spotify data: {e}")
        return {"error": str(e)}

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
