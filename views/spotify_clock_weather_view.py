from .spotify_base_view import SpotifyBaseView
from widgets import WorldClockWidget, WeatherWidget

class SpotifyClockWeatherView(SpotifyBaseView):
    def __init__(self, config, screen_width, screen_height, debug=False):
        super().__init__(config, screen_width, screen_height, debug=debug)
        
        clock_cfg = config["widgets"]["world_clock"]
        self.world_clock_widget = WorldClockWidget(
            reference_location=clock_cfg["reference_location"],
            clocks=clock_cfg["clocks"],
            home_cycle_interval=clock_cfg["home_cycle_interval"],
            other_cycle_interval=clock_cfg["other_cycle_interval"]
        )
        
        cities = [c["name"] for c in clock_cfg["clocks"]]
        self.weather_widget = WeatherWidget(cities=cities, api_poll_interval=300)

    def update(self, events, current_time, test_error=False):
        super().update(events, current_time, test_error=test_error)
        self.world_clock_widget.update(current_time)
        self.weather_widget.update(current_time)

    def draw_header(self, screen):
        active_city = self.world_clock_widget.clocks[self.world_clock_widget.clock_index]
        
        # 1. Clock on line 1
        clock_str = self.world_clock_widget.get_display_string()
        clock_surf = self.font_medium_bold.render(clock_str, True, (179, 179, 179))
        clock_rect = clock_surf.get_rect(topright=(self.width - self.margin, self.margin))
        screen.blit(clock_surf, clock_rect)
        
        # 2. Weather on line 2 (exclude city location, as it's shown in the clock above)
        weather_str = self.weather_widget.get_weather(active_city["name"], include_location=False)
        weather_surf = self.font_small.render(weather_str, True, (179, 179, 179))
        weather_rect = weather_surf.get_rect(topright=(self.width - self.margin, clock_rect.bottom + 5))
        screen.blit(weather_surf, weather_rect)
