import os
import io
import time
import requests
import pygame
import re
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

def clean_track_name(name):
    """
    Cleans song titles by removing common extra text (such as "feat. ...",
    "with ...", "Remastered", "Radio Edit", "Live", etc.).
    """
    if not name:
        return name
    
    keywords = [
        r'feat\.?', r'featuring', r'with', r'remaster(ed)?', r'live', r'acoustic', 
        r'radio\s+edit', r'edit', r'bonus', r'single', r'deluxe', r'extended', 
        r'original\s+mix', r'mix', r'version', r'instrumental', r'edition', r'mono', r'stereo'
    ]
    
    keywords_pattern = '|'.join(keywords)
    paren_regex = re.compile(
        r'\s*[\(\[][^\]\)]*(?:' + keywords_pattern + r')[^\]\)]*[\)\]]',
        re.IGNORECASE
    )
    
    hyphen_regex = re.compile(
        r'\s*-\s*.*?(?:' + keywords_pattern + r').*',
        re.IGNORECASE
    )
    
    cleaned = name
    cleaned = hyphen_regex.sub('', cleaned)
    cleaned = paren_regex.sub('', cleaned)
    cleaned = cleaned.strip()
    return cleaned if cleaned else name

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
                'name': clean_track_name(item.get('name', 'Unknown Track')),
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


class SpotifyWidget:
    def __init__(self, api_poll_interval=30, debug=False):
        self.api_poll_interval = api_poll_interval
        self.debug = debug
        self.sp = get_spotify_client()
        self.track_info = None
        self.last_sync_time = 0
        self.error_message = None
        
        # Album Art Cache
        self.album_art = None
        self.current_cover_url = None

    def fetch_album_art(self, url, size):
        if url == self.current_cover_url and self.album_art:
            return self.album_art
            
        try:
            response = requests.get(url)
            image_data = io.BytesIO(response.content)
            raw_image = pygame.image.load(image_data)
            self.album_art = pygame.transform.smoothscale(raw_image, (size, size))
            self.current_cover_url = url
            return self.album_art
        except Exception as e:
            print(f"Error loading album art: {e}")
            self.album_art = None
            return None

    def update(self, current_time=None, album_art_size=None, test_error=False):
        if current_time is None:
            current_time = time.time()
            
        should_sync = (current_time - self.last_sync_time > self.api_poll_interval)
        
        # Smart Sync: If song is playing and should have finished (plus 1s buffer)
        if self.track_info and self.track_info['is_playing']:
            progress_ms = get_interpolated_progress(self.track_info, self.last_sync_time)
            if progress_ms >= self.track_info['duration_ms']:
                # Poll again if we haven't checked in at least 2 seconds
                if current_time - self.last_sync_time > 2:
                    should_sync = True

        if should_sync:
            if test_error:
                new_info = {"error": "Simulated API Error for testing"}
            else:
                new_info = get_current_track_info(self.sp, debug=self.debug)
            
            if new_info:
                if "error" in new_info:
                    self.error_message = new_info["error"]
                    self.track_info = None
                else:
                    self.error_message = None
                    if not self.track_info or new_info['name'] != self.track_info['name']:
                        print(f"Song transition detected: {new_info['name']}")
                        
                    self.track_info = new_info
                    if self.track_info['cover_url'] and album_art_size:
                        self.fetch_album_art(self.track_info['cover_url'], album_art_size)
                
                self.last_sync_time = current_time
            else:
                self.track_info = None
                self.error_message = None
                self.last_sync_time = current_time # Still update to respect interval
                
        # If track info is present and art size is specified, ensure it is loaded
        if self.track_info and self.track_info['cover_url'] and album_art_size and not self.album_art:
            self.fetch_album_art(self.track_info['cover_url'], album_art_size)
