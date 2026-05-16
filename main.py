import os
import time
import requests
import pygame
import io
import argparse
from datetime import datetime
import pytz
from spotify import get_spotify_client, get_current_track_info, get_interpolated_progress

# --- Constants ---

DEFAULT_WINDOW_WIDTH = 1024
DEFAULT_WINDOW_HEIGHT = 600
FPS = 60

# World Clock Config
REFERENCE_LOCATION = "AUS" # Our "Home" location
WORLD_CLOCKS = [
    {"name": "SFO", "tz": "America/Los_Angeles"},
    {"name": "AUS", "tz": "America/Chicago"},
    {"name": "PIT", "tz": "America/New_York"},
    # {"name": "LON", "tz": "Europe/London"},
    # {"name": "HKG", "tz": "Asia/Hong_Kong"},
    # {"name": "TYO", "tz": "Asia/Tokyo"},
]
HOME_CLOCK_CYCLE_INTERVAL = 30 # Seconds for the home city
OTHER_CLOCK_CYCLE_INTERVAL = 15 # Seconds for every other city


# Colors
COLOR_BG = (18, 18, 18)        # Spotify Dark

COLOR_TEXT_MAIN = (255, 255, 255)
COLOR_TEXT_SUB = (179, 179, 179)

# COLOR_PROGRESS_BAR = (30, 215, 96) # Spotify Green
COLOR_PROGRESS_BAR = (198, 160, 246) 
COLOR_PROGRESS_BG = (64, 64, 64)

class SpotifyDisplay:
    def __init__(self, width, height, allow_dimming=True):
        if width <= height:
            print(f"Warning: Window width ({width}) should be greater than height ({height}) for optimal layout.")
            
        pygame.init()
        self.width = width
        self.height = height
        self.margin = int(height * 0.08)
        self.album_art_size = height - (2 * self.margin)
        self.allow_dimming = allow_dimming

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Spotify Widget")
        self.clock = pygame.time.Clock()
        
        # Scalable font loading
        base_size = height
        self.font_large = pygame.font.SysFont("Arial", int(base_size * 0.06), bold=True)
        self.font_medium = pygame.font.SysFont("Arial", int(base_size * 0.045))
        self.font_medium_bold = pygame.font.SysFont("Arial", int(base_size * 0.045), bold=True)
        self.font_small = pygame.font.SysFont("Arial", int(base_size * 0.03))
        
        # State
        self.sp = get_spotify_client()
        self.track_info = None
        self.last_sync_time = 0
        self.album_art = None
        self.current_cover_url = None
        
        # Clock State
        self.clock_index = 0
        self.last_clock_cycle = time.time()
        
        # Dimming State
        self.dimmed = False
        self.dim_surface = pygame.Surface((self.width, self.height))
        self.dim_surface.set_alpha(180) # 0 is transparent, 255 is solid black
        self.dim_surface.fill((0, 0, 0))
        
        self.api_poll_interval = 30
        
    def fetch_album_art(self, url):
        if url == self.current_cover_url and self.album_art:
            return
            
        try:
            response = requests.get(url)
            image_data = io.BytesIO(response.content)
            raw_image = pygame.image.load(image_data)
            self.album_art = pygame.transform.smoothscale(raw_image, (self.album_art_size, self.album_art_size))
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

    def draw_world_clock(self):
        """
        Draws the world clock in the top right corner.
        """
        now_utc = datetime.now(pytz.utc)
        
        # Get Reference (Home) info
        home_tz = pytz.timezone(next(c["tz"] for c in WORLD_CLOCKS if c["name"] == REFERENCE_LOCATION))
        home_time = now_utc.astimezone(home_tz)
        
        # Get Current Cycle info
        city = WORLD_CLOCKS[self.clock_index]
        city_tz = pytz.timezone(city["tz"])
        city_time = now_utc.astimezone(city_tz)
        
        # Format time: 10:42:05 and date: 15.05.26
        time_str = city_time.strftime("%H:%M:%S")
        date_str = city_time.strftime("%d.%m.%y")
        
        # Day offset logic
        day_offset = ""
        # Compare dates using the local dates of each timezone
        if city_time.date() > home_time.date():
            day_offset = " (+1)"
        elif city_time.date() < home_time.date():
            day_offset = " (-1)"
            
        prefix = "*" if city["name"] == REFERENCE_LOCATION else ""
        # Format: *CITY: HH:MM | MM.DD (+1)
        display_str = f"{prefix}{city['name'].upper()}: {time_str} | {date_str}{day_offset}".lower()
        # Ensure city code is still uppercase
        display_str = display_str.replace(city['name'].lower(), city['name'].upper())
        
        # Render
        text_surf = self.font_medium_bold.render(display_str, True, COLOR_TEXT_SUB)
        rect = text_surf.get_rect(topright=(self.width - self.margin, self.margin))
        self.screen.blit(text_surf, rect)

    def get_wrapped_text(self, text, font, max_width, max_lines=3):
        """
        Wraps text into multiple lines based on max_width.
        Truncates the last line with ellipses if text exceeds max_lines.
        """
        text = str(text).lower()
        words = text.split(' ')
        lines = []
        current_line = []

        for i, word in enumerate(words):
            # Check if adding this word exceeds max_width
            test_line = ' '.join(current_line + [word])
            
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                # Need to start a new line
                if current_line:
                    lines.append(' '.join(current_line))
                
                if len(lines) == max_lines - 1:
                    # This was the second to last line, and we still have more words.
                    # The current word + all remaining words must be fit/truncated on the LAST line.
                    remaining_text = ' '.join(words[i:])
                    last_line = remaining_text
                    
                    if font.size(last_line)[0] > max_width:
                        # Truncate last line with ellipses
                        for j in range(len(last_line), 0, -1):
                            truncated = last_line[:j] + "..."
                            if font.size(truncated)[0] <= max_width:
                                last_line = truncated
                                break
                    lines.append(last_line)
                    current_line = []
                    break
                else:
                    current_line = [word]
                    # Check if a single word is already too long for a fresh line
                    if font.size(word)[0] > max_width:
                        for j in range(len(word), 0, -1):
                            truncated = word[:j] + "..."
                            if font.size(truncated)[0] <= max_width:
                                lines[-1] = truncated # This is slightly wrong, should be current line
                                break
        
        if current_line and len(lines) < max_lines:
            lines.append(' '.join(current_line))
            
        return lines

    def draw(self):
        self.screen.fill(COLOR_BG)
        
        # World Clock
        self.draw_world_clock()
        
        if not self.track_info:
            text = "no music playing"
            text_surf = self.font_medium.render(text, True, COLOR_TEXT_SUB)
            rect = text_surf.get_rect(center=(self.width // 2, self.height // 2))
            self.screen.blit(text_surf, rect)
        else:
            # 1. Draw Album Art
            art_x = self.margin
            art_y = self.margin
            if self.album_art:
                self.screen.blit(self.album_art, (art_x, art_y))
            else:
                pygame.draw.rect(self.screen, COLOR_PROGRESS_BG, (art_x, art_y, self.album_art_size, self.album_art_size))
            
            # 2. Draw Text Info (Bottom Aligned)
            text_x = art_x + self.album_art_size + self.margin
            bottom_y = art_y + self.album_art_size
            max_text_width = self.width - text_x - self.margin
            
            # Progress Bar (Lowest element)
            progress_ms = get_interpolated_progress(self.track_info, self.last_sync_time)
            duration_ms = self.track_info['duration_ms']
            progress_ratio = min(progress_ms / duration_ms, 1.0)
            
            bar_width = max_text_width
            bar_height = 8
            bar_y = bottom_y - int(self.margin * 0.6)
            
            # Draw Progress Bar
            pygame.draw.rect(self.screen, COLOR_PROGRESS_BG, (text_x, bar_y, bar_width, bar_height), border_radius=4)
            pygame.draw.rect(self.screen, COLOR_PROGRESS_BAR, (text_x, bar_y, int(bar_width * progress_ratio), bar_height), border_radius=4)
            
            # Time Text (under bar)
            time_str = self.format_time(progress_ms, duration_ms)
            if not self.track_info['is_playing']:
                time_str = f"[paused] {time_str}"
            
            # Debugging NULL pointer error
            if not isinstance(time_str, str) or not time_str:
                time_str = "00:00 / 00:00"
            
            try:
                time_surf = self.font_small.render(time_str.lower(), True, COLOR_TEXT_SUB)
                self.screen.blit(time_surf, (text_x, bar_y + 15))
            except Exception as e:
                print(f"Failed to render time: {e}")

            # Text spacing logic
            line_y = bar_y - self.margin
            
            # Album (above bar)
            self.render_lowercase_truncated(self.track_info['album'], self.font_small, COLOR_TEXT_SUB, max_text_width, (text_x, line_y))
            
            # Artist (above album)
            line_y -= int(self.margin * 0.9)
            self.render_lowercase_truncated(self.track_info['artist'], self.font_medium, COLOR_TEXT_SUB, max_text_width, (text_x, line_y))
            
            # Song Name (above artist) - Multi-line
            wrapped_name = self.get_wrapped_text(self.track_info['name'], self.font_large, max_text_width, max_lines=3)
            
            # Draw lines from bottom to top
            for line in reversed(wrapped_name):
                line_y -= int(self.margin * 1.1)
                self.render_lowercase_truncated(line, self.font_large, COLOR_TEXT_MAIN, max_text_width, (text_x, line_y))

        # Apply Dimming Overlay
        if self.dimmed:
            self.screen.blit(self.dim_surface, (0, 0))

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
                elif event.type == pygame.MOUSEBUTTONDOWN and self.allow_dimming:
                    # Check if click is in the middle of the screen (10% margin on each side)
                    zone_w = int(self.width * 0.8)
                    zone_h = int(self.height * 0.8)
                    center_rect = pygame.Rect(int(self.width * 0.1), int(self.height * 0.1), zone_w, zone_h)
                    if center_rect.collidepoint(event.pos):
                        self.dimmed = not self.dimmed
            
            # World Clock Cycling
            current_city = WORLD_CLOCKS[self.clock_index]
            interval = HOME_CLOCK_CYCLE_INTERVAL if current_city["name"] == REFERENCE_LOCATION else OTHER_CLOCK_CYCLE_INTERVAL
            
            if current_time - self.last_clock_cycle > interval:
                self.clock_index = (self.clock_index + 1) % len(WORLD_CLOCKS)
                self.last_clock_cycle = current_time

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
    parser = argparse.ArgumentParser(description="Spotify Display Widget")
    parser.add_argument("--width", type=int, default=DEFAULT_WINDOW_WIDTH, help="Window width")
    parser.add_argument("--height", type=int, default=DEFAULT_WINDOW_HEIGHT, help="Window height")
    parser.add_argument("--no-dim", action="store_false", dest="allow_dimming", help="Disable click-to-dim feature")
    parser.set_defaults(allow_dimming=True)
    
    args = parser.parse_args()
    
    display = SpotifyDisplay(args.width, args.height, args.allow_dimming)
    display.run()
