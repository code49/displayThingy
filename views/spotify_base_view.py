import pygame
from .base_view import BaseView
from widgets import SpotifyWidget
from widgets.spotify import get_interpolated_progress

# --- Colors ---
COLOR_BG = (18, 18, 18)        # Spotify Dark
COLOR_TEXT_MAIN = (255, 255, 255)
COLOR_TEXT_SUB = (179, 179, 179)
COLOR_PROGRESS_BAR = (198, 160, 246) 
COLOR_PROGRESS_BG = (64, 64, 64)

class SpotifyBaseView(BaseView):
    def __init__(self, config, screen_width, screen_height, debug=False):
        super().__init__(config)
        self.width = screen_width
        self.height = screen_height
        self.debug = debug
        
        # Geometry
        self.margin = int(self.height * 0.08)
        self.album_art_size = self.height - (2 * self.margin)
        
        # Scaling fonts
        base_size = self.height
        self.font_large = pygame.font.SysFont("Arial", int(base_size * 0.06), bold=True)
        self.font_medium = pygame.font.SysFont("Arial", int(base_size * 0.045))
        self.font_medium_bold = pygame.font.SysFont("Arial", int(base_size * 0.045), bold=True)
        self.font_small = pygame.font.SysFont("Arial", int(base_size * 0.03))
        
        spotify_cfg = config.get("widgets", {}).get("spotify", {"api_poll_interval": 30})
        self.spotify_widget = SpotifyWidget(
            api_poll_interval=spotify_cfg.get("api_poll_interval", 30),
            debug=self.debug
        )
        
        # Dimming Overlay
        window_cfg = config.get("window", {})
        self.allow_dimming = window_cfg.get("allow_dimming", True)
        self.dimmed = False
        self.dim_surface = pygame.Surface((self.width, self.height))
        self.dim_surface.set_alpha(180) # 0 transparent, 255 opaque
        self.dim_surface.fill((0, 0, 0))

    def update(self, events, current_time, test_error=False):
        # Process events for local view interaction (dimming)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and self.allow_dimming:
                # Check if click is in the middle of the screen (10% margin on each side)
                zone_w = int(self.width * 0.8)
                zone_h = int(self.height * 0.8)
                center_rect = pygame.Rect(int(self.width * 0.1), int(self.height * 0.1), zone_w, zone_h)
                if center_rect.collidepoint(event.pos):
                    self.dimmed = not self.dimmed
                    
        # Update widgets
        self.spotify_widget.update(current_time, album_art_size=self.album_art_size, test_error=test_error)

    def draw_header(self, screen):
        """
        Subclasses should override this method to draw their own custom widgets
        (like world clock, weather, etc.) in the top-right header area.
        """
        pass

    def render_lowercase_truncated(self, screen, text, font, color, max_width, dest):
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
            screen.blit(surf, dest)
        except Exception as e:
            print(f"Failed to render text '{text}': {e}")

    def get_wrapped_text(self, text, font, max_width, max_lines=2):
        """
        Wraps text into multiple lines based on max_width.
        Truncates the last line with ellipses if text exceeds max_lines.
        """
        text = str(text).lower()
        words = text.split(' ')
        lines = []
        current_line = []

        for i, word in enumerate(words):
            test_line = ' '.join(current_line + [word])
            
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                
                if len(lines) == max_lines - 1:
                    remaining_text = ' '.join(words[i:])
                    last_line = remaining_text
                    
                    if font.size(last_line)[0] > max_width:
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
                    if font.size(word)[0] > max_width:
                        for j in range(len(word), 0, -1):
                            truncated = word[:j] + "..."
                            if font.size(truncated)[0] <= max_width:
                                current_line = [truncated]
                                break
        
        if current_line and len(lines) < max_lines:
            lines.append(' '.join(current_line))
            
        return lines

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

    def draw(self, screen):
        screen.fill(COLOR_BG)
        
        # 1. Draw view-specific header
        self.draw_header(screen)
        
        track_info = self.spotify_widget.track_info
        error_message = self.spotify_widget.error_message
        
        if not track_info:
            text = "no music playing"
            text_surf = self.font_medium.render(text, True, COLOR_TEXT_SUB)
            rect = text_surf.get_rect(center=(self.width // 2, self.height // 2))
            screen.blit(text_surf, rect)
            
            if error_message:
                error_text = f"warning: {error_message}"
                wrapped_error = self.get_wrapped_text(error_text, self.font_small, self.width * 0.8, max_lines=2)
                
                error_y = rect.bottom + 20
                for line in wrapped_error:
                    line_surf = self.font_small.render(line, True, (200, 80, 80)) # Reddish
                    line_rect = line_surf.get_rect(midtop=(self.width // 2, error_y))
                    screen.blit(line_surf, line_rect)
                    error_y += line_surf.get_height() + 5
        else:
            # 1. Draw Album Art
            art_x = self.margin
            art_y = self.margin
            album_art = self.spotify_widget.album_art
            
            if album_art:
                screen.blit(album_art, (art_x, art_y))
            else:
                pygame.draw.rect(screen, COLOR_PROGRESS_BG, (art_x, art_y, self.album_art_size, self.album_art_size))
            
            # 2. Draw Text Info (Bottom Aligned)
            text_x = art_x + self.album_art_size + self.margin
            bottom_y = art_y + self.album_art_size
            max_text_width = self.width - text_x - self.margin
            
            # Progress Bar (Lowest element)
            progress_ms = get_interpolated_progress(track_info, self.spotify_widget.last_sync_time)
            duration_ms = track_info['duration_ms']
            progress_ratio = min(progress_ms / duration_ms, 1.0)
            
            bar_width = max_text_width
            bar_height = 8
            bar_y = bottom_y - int(self.margin * 0.6)
            
            # Draw Progress Bar
            pygame.draw.rect(screen, COLOR_PROGRESS_BG, (text_x, bar_y, bar_width, bar_height), border_radius=4)
            pygame.draw.rect(screen, COLOR_PROGRESS_BAR, (text_x, bar_y, int(bar_width * progress_ratio), bar_height), border_radius=4)
            
            # Time Text (under bar)
            time_str = self.format_time(progress_ms, duration_ms)
            if not track_info['is_playing']:
                time_str = f"[paused] {time_str}"
            
            if not isinstance(time_str, str) or not time_str:
                time_str = "00:00 / 00:00"
            
            try:
                time_surf = self.font_small.render(time_str.lower(), True, COLOR_TEXT_SUB)
                screen.blit(time_surf, (text_x, bar_y + 15))
            except Exception as e:
                print(f"Failed to render time: {e}")

            # Text spacing logic
            line_y = bar_y - self.margin
            
            # Album / Show Name (above bar)
            self.render_lowercase_truncated(screen, track_info['album'], self.font_small, COLOR_TEXT_SUB, max_text_width, (text_x, line_y))
            
            # Artist / Publisher (above album)
            line_y -= int(self.margin * 0.9)
            self.render_lowercase_truncated(screen, track_info['artist'], self.font_medium, COLOR_TEXT_SUB, max_text_width, (text_x, line_y))

            # Song Name (above artist) - Multi-line
            wrapped_name = self.get_wrapped_text(track_info['name'], self.font_large, max_text_width, max_lines=2)
            
            for line in reversed(wrapped_name):
                line_y -= int(self.margin * 1.1)
                self.render_lowercase_truncated(screen, line, self.font_large, COLOR_TEXT_MAIN, max_text_width, (text_x, line_y))

            # Type indicator (Podcast vs Track) - Above the Name
            if track_info.get('type') == 'podcast':
                type_surf = self.font_small.render("[PODCAST]", True, COLOR_PROGRESS_BAR)
                screen.blit(type_surf, (text_x, line_y - int(self.margin * 0.6)))

        # Apply Dimming Overlay
        if self.dimmed:
            screen.blit(self.dim_surface, (0, 0))
