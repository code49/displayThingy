from .spotify_base_view import SpotifyBaseView

class SpotifyOnlyView(SpotifyBaseView):
    def __init__(self, config, screen_width, screen_height, debug=False):
        super().__init__(config, screen_width, screen_height, debug=debug)

    def draw_header(self, screen):
        # Empty header area (Spotify playback only)
        pass
