from .base_view import BaseView
from .spotify_base_view import SpotifyBaseView
from .spotify_only_view import SpotifyOnlyView
from .spotify_clock_view import SpotifyClockView
from .spotify_weather_view import SpotifyWeatherView
from .spotify_clock_weather_view import SpotifyClockWeatherView

VIEWS = {
    "spotify": SpotifyOnlyView,
    "spotify_clock": SpotifyClockView,
    "spotify_weather": SpotifyWeatherView,
    "spotify_clock_weather": SpotifyClockWeatherView
}

def get_view_class(name):
    return VIEWS.get(name)
