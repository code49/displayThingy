import os
import json
import argparse
import time
import pygame
from views import get_view_class
from widgets.spotify import get_current_track_info

# --- Default Constants (Fallback if configs.json is missing) ---
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 720
DEFAULT_FPS = 60

class SpotifyDisplay:
    def __init__(self, width=None, height=None, allow_dimming=None, fullscreen=None, fps=None, profile=None, show_clock=None, show_weather=None, debug=False, config_path="configs.json"):
        # 1. Load config
        self.config = self.load_config(config_path)
        self.debug = debug

        # Resolve active profile configuration
        self.profile_name = profile if profile is not None else self.config.get("active_profile", "default")
        profile_cfg = self.config.get("profiles", {}).get(self.profile_name, {})
        if not profile_cfg and self.profile_name != "default":
            print(f"Warning: Profile '{self.profile_name}' not found. Falling back to default.")
            profile_cfg = self.config.get("profiles", {}).get("default", {})
            self.profile_name = "default"

        # Load window configuration from profile
        window_cfg = profile_cfg.get("window", {})
        
        # Merge CLI arguments with profile/config window settings
        self.width = width if width is not None else window_cfg.get("width", DEFAULT_WINDOW_WIDTH)
        self.height = height if height is not None else window_cfg.get("height", DEFAULT_WINDOW_HEIGHT)
        self.fps = fps if fps is not None else window_cfg.get("fps", DEFAULT_FPS)
        self.fullscreen = fullscreen if fullscreen is not None else window_cfg.get("fullscreen", False)
        
        # Build window configuration dictionary for the runtime config
        self.window_cfg = self.config.setdefault("window", {})
        self.window_cfg["width"] = self.width
        self.window_cfg["height"] = self.height
        self.window_cfg["fps"] = self.fps
        self.window_cfg["fullscreen"] = self.fullscreen
        
        actual_allow_dimming = allow_dimming if allow_dimming is not None else window_cfg.get("allow_dimming", True)
        self.window_cfg["allow_dimming"] = actual_allow_dimming
        
        # Resolve active view name
        active_view_name = profile_cfg.get("active_view", "spotify_clock")
        
        # Translate old command line boolean flags for backwards compatibility if explicitly set
        if show_clock is not None or show_weather is not None:
            has_clock = "clock" in active_view_name
            has_weather = "weather" in active_view_name
            
            final_clock = show_clock if show_clock is not None else has_clock
            final_weather = show_weather if show_weather is not None else has_weather
            
            if final_clock and final_weather:
                active_view_name = "spotify_clock_weather"
            elif final_clock:
                active_view_name = "spotify_clock"
            elif final_weather:
                active_view_name = "spotify_weather"
            else:
                active_view_name = "spotify"
                
        # Store resolved view name back in configs
        self.config["active_view"] = active_view_name
        
        pygame.init()
        
        if self.fullscreen:
            info = pygame.display.Info()
            self.width = info.current_w
            self.height = info.current_h
            flags = pygame.FULLSCREEN | pygame.NOFRAME
        else:
            flags = 0

        if self.width <= self.height:
            print(f"Warning: Window width ({self.width}) should be greater than height ({self.height}) for optimal layout.")

        self.screen = pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption("Spotify Widget")
        self.clock = pygame.time.Clock()
        
        # Load and instantiate active view
        view_cls = get_view_class(active_view_name)
        if not view_cls:
            raise ValueError(f"Unknown view: {active_view_name}")
            
        self.view = view_cls(self.config, self.width, self.height, debug=self.debug)

    def load_config(self, path):
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load config from {path}: {e}")
        return {}

    # --- Property wrappers for backward compatibility and testing ---
    @property
    def error_message(self):
        if hasattr(self, 'view') and hasattr(self.view, 'spotify_widget'):
            return self.view.spotify_widget.error_message
        return None

    @error_message.setter
    def error_message(self, val):
        if hasattr(self, 'view') and hasattr(self.view, 'spotify_widget'):
            self.view.spotify_widget.error_message = val

    @property
    def track_info(self):
        if hasattr(self, 'view') and hasattr(self.view, 'spotify_widget'):
            return self.view.spotify_widget.track_info

        return None

    @track_info.setter
    def track_info(self, val):
        if hasattr(self, 'view') and hasattr(self.view, 'spotify_widget'):
            self.view.spotify_widget.track_info = val

    @property
    def api_poll_interval(self):
        if hasattr(self, 'view') and hasattr(self.view, 'spotify_widget'):
            return self.view.spotify_widget.api_poll_interval
        return 30

    @api_poll_interval.setter
    def api_poll_interval(self, val):
        if hasattr(self, 'view') and hasattr(self.view, 'spotify_widget'):
            self.view.spotify_widget.api_poll_interval = val

    def run(self, test_error=False):
        running = True
        while running:
            current_time = time.time()
            events = pygame.event.get()
            
            # Handle basic quit/close events
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        
            # Delegate event processing and updates to active view
            self.view.update(events, current_time, test_error=test_error)
            
            # Delegate drawing
            self.view.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(self.fps)
            
        pygame.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spotify Display Widget")
    parser.add_argument("--width", type=int, help="Window width")
    parser.add_argument("--height", type=int, help="Window height")
    parser.add_argument("--fps", type=int, help="Target frames per second")
    parser.add_argument("--no-dim", action="store_false", dest="allow_dimming", help="Disable click-to-dim feature")
    parser.add_argument("--fullscreen", action="store_true", help="Run the display in fullscreen mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--test-error", action="store_true", help="Simulate a Spotify API error for testing")
    parser.add_argument("--show-clock", dest="show_clock", action="store_true", default=None, help="Show world clock")
    parser.add_argument("--no-clock", dest="show_clock", action="store_false", default=None, help="Hide world clock")
    parser.add_argument("--show-weather", dest="show_weather", action="store_true", default=None, help="Show weather report")
    parser.add_argument("--no-weather", dest="show_weather", action="store_false", default=None, help="Hide weather report")
    parser.add_argument("--profile", "-p", type=str, help="Configuration profile to run (e.g. raspi, framework13)")
    
    args = parser.parse_args()
    
    # Passing None values where parameters are omitted, letting configs.json default rule.
    display = SpotifyDisplay(
        width=args.width,
        height=args.height,
        allow_dimming=None if args.allow_dimming else False,
        fullscreen=True if args.fullscreen else None,
        fps=args.fps,
        profile=args.profile,
        show_clock=args.show_clock,
        show_weather=args.show_weather,
        debug=args.debug
    )
    display.run(test_error=args.test_error)
