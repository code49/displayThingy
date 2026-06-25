from .base_view import BaseView
from .spotify_clock_view import SpotifyClockView

VIEWS = {
    "spotify_clock": SpotifyClockView
}

def get_view_class(name):
    return VIEWS.get(name)
