import os
import time
import requests
import pygame
import io
from spotify import get_spotify_client, get_current_track_info, get_interpolated_progress

# --- Constants ---
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 600
ALBUM_ART_SIZE = 450
FPS = 60

# Colors
COLOR_BG = (18, 18, 18)        # Spotify Dark

COLOR_TEXT_MAIN = (255, 255, 255)
COLOR_TEXT_SUB = (179, 179, 179)

# COLOR_PROGRESS_BAR = (30, 215, 96) # Spotify Green
COLOR_PROGRESS_BAR = (198, 160, 246) 
COLOR_PROGRESS_BG = (64, 64, 64)

class SpotifyDisplay:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Spotify Widget")
        self.clock = pygame.time.Clock()
        
        # Simple, stable font loading with Arial
        self.font_large = pygame.font.SysFont("Arial", 36, bold=True)
        self.font_medium = pygame.font.SysFont("Arial", 28)
        self.font_small = pygame.font.SysFont("Arial", 20)
        
        # State
        self.sp = get_spotify_client()
        self.track_info = None
        self.last_sync_time = 0
        self.album_art = None
        self.current_cover_url = None
        
        self.api_poll_interval = 30
        
    def fetch_album_art(self, url):
        if url == self.current_cover_url and self.album_art:
            return
            
        try:
            response = requests.get(url)
            image_data = io.BytesIO(response.content)
            raw_image = pygame.image.load(image_data)
            self.album_art = pygame.transform.smoothscale(raw_image, (ALBUM_ART_SIZE, ALBUM_ART_SIZE))
            self.current_cover_url = url
        except Exception as e:
            print(f"Error loading album art: {e}")
            self.album_art = None

    def render_lowercase_truncated(self, text, font, color, max_width, dest):
        """
        Converts text to lowercase and truncates with ellipses if too long.
        """
        try:
            text = str(text).lower()
            if font.size(text)[0] > max_width:
                # Simple truncation loop
                for i in range(len(text), 0, -1):
                    truncated = text[:i] + "..."
                    if font.size(truncated)[0] <= max_width:
                        text = truncated
                        break
            
            surf = font.render(text, True, color)
            self.screen.blit(surf, dest)
        except Exception as e:
            print(f"Failed to render text '{text}': {e}")
            # Optional: render a placeholder or just skip

    def draw(self):
        self.screen.fill(COLOR_BG)
        
        if not self.track_info:
            text = "no music playing"
            text_surf = self.font_medium.render(text, True, COLOR_TEXT_SUB)
            rect = text_surf.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2))
            self.screen.blit(text_surf, rect)
        else:
            # 1. Draw Album Art
            art_x = 40
            art_y = (WINDOW_HEIGHT - ALBUM_ART_SIZE) // 2
            if self.album_art:
                self.screen.blit(self.album_art, (art_x, art_y))
            else:
                pygame.draw.rect(self.screen, COLOR_PROGRESS_BG, (art_x, art_y, ALBUM_ART_SIZE, ALBUM_ART_SIZE))
            
            # 2. Draw Text Info (Bottom Aligned)
            text_x = art_x + ALBUM_ART_SIZE + 40
            bottom_y = art_y + ALBUM_ART_SIZE
            max_text_width = WINDOW_WIDTH - text_x - 40
            
            # Progress Bar (Lowest element)
            progress_ms = get_interpolated_progress(self.track_info, self.last_sync_time)
            duration_ms = self.track_info['duration_ms']
            progress_ratio = min(progress_ms / duration_ms, 1.0)
            
            bar_width = max_text_width
            bar_height = 8
            bar_y = bottom_y - 30
            
            # Draw Progress Bar
            pygame.draw.rect(self.screen, COLOR_PROGRESS_BG, (text_x, bar_y, bar_width, bar_height), border_radius=4)
            pygame.draw.rect(self.screen, COLOR_PROGRESS_BAR, (text_x, bar_y, int(bar_width * progress_ratio), bar_height), border_radius=4)
            
            # Time Text (under bar)
            time_str = self.format_time(progress_ms, duration_ms)
            
            # Debugging NULL pointer error
            if not isinstance(time_str, str) or not time_str:
                time_str = "00:00 / 00:00"
            
            try:
                time_surf = self.font_small.render(time_str.lower(), True, COLOR_TEXT_SUB)
                self.screen.blit(time_surf, (text_x, bar_y + 15))
            except Exception as e:
                print(f"Failed to render time: {e}")

            # Text spacing logic
            line_y = bar_y - 50 # Start 50px above bar
            
            # Album (above bar)
            self.render_lowercase_truncated(self.track_info['album'], self.font_small, COLOR_TEXT_SUB, max_text_width, (text_x, line_y))
            
            # Artist (above album)
            line_y -= 45
            self.render_lowercase_truncated(self.track_info['artist'], self.font_medium, COLOR_TEXT_SUB, max_text_width, (text_x, line_y))
            
            # Song Name (above artist)
            line_y -= 55
            self.render_lowercase_truncated(self.track_info['name'], self.font_large, COLOR_TEXT_MAIN, max_text_width, (text_x, line_y))

        pygame.display.flip()

    def format_time(self, current_ms, duration_ms):
        """
        Formats ms into a string, ensuring 0-filling and consistent length.
        Uses HH:MM:SS if the song is > 1 hour, otherwise MM:SS.
        """
        def to_str(ms, include_hours):
            total_seconds = int(ms // 1000)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if include_hours:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes:02d}:{seconds:02d}"

        show_hours = duration_ms >= 3600000
        return f"{to_str(current_ms, show_hours)} / {to_str(duration_ms, show_hours)}"

    def run(self):
        running = True
        while running:
            current_time = time.time()
            
            # Handle Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            # API Sync Logic
            should_sync = (current_time - self.last_sync_time > self.api_poll_interval)
            
            # Smart Sync: If song is playing and should have finished (plus 1s buffer)
            if self.track_info and self.track_info['is_playing']:
                progress_ms = get_interpolated_progress(self.track_info, self.last_sync_time)
                if progress_ms >= self.track_info['duration_ms']:
                    # Poll again if we haven't checked in at least 2 seconds 
                    # (prevents spamming if Spotify is slow to transition)
                    if current_time - self.last_sync_time > 2:
                        should_sync = True

            if should_sync:
                new_info = get_current_track_info(self.sp)
                if new_info:
                    # Check if the song actually changed or if progress reset
                    # This helps debug/log transitions
                    if not self.track_info or new_info['name'] != self.track_info['name']:
                        print(f"Song transition detected: {new_info['name']}")
                        
                    self.track_info = new_info
                    self.last_sync_time = current_time
                    if self.track_info['cover_url']:
                        self.fetch_album_art(self.track_info['cover_url'])
                else:
                    self.track_info = None
                    self.last_sync_time = current_time # Still update sync time to respect interval
            
            self.draw()
            self.clock.tick(FPS)
            
        pygame.quit()

if __name__ == "__main__":
    display = SpotifyDisplay()
    display.run()
