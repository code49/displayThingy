import time
from datetime import datetime
import pytz

class WorldClockWidget:
    def __init__(self, reference_location, clocks, home_cycle_interval, other_cycle_interval):
        self.reference_location = reference_location
        self.clocks = clocks
        self.home_cycle_interval = home_cycle_interval
        self.other_cycle_interval = other_cycle_interval
        
        self.clock_index = 0
        self.last_clock_cycle = time.time()

    def update(self, current_time=None):
        if current_time is None:
            current_time = time.time()
            
        current_city = self.clocks[self.clock_index]
        interval = (self.home_cycle_interval 
                    if current_city["name"] == self.reference_location 
                    else self.other_cycle_interval)
        
        if current_time - self.last_clock_cycle > interval:
            self.clock_index = (self.clock_index + 1) % len(self.clocks)
            self.last_clock_cycle = current_time

    def get_display_string(self):
        """
        Computes and formats the current world clock display string.
        Format: *CITY: HH:MM:SS | DD.MM.YY (+1)
        """
        now_utc = datetime.now(pytz.utc)
        
        # Get Reference (Home) info
        home_city_cfg = next((c for c in self.clocks if c["name"] == self.reference_location), None)
        if not home_city_cfg:
            home_city_cfg = self.clocks[0]
            
        home_tz = pytz.timezone(home_city_cfg["tz"])
        home_time = now_utc.astimezone(home_tz)
        
        # Get Current City info
        city = self.clocks[self.clock_index]
        city_tz = pytz.timezone(city["tz"])
        city_time = now_utc.astimezone(city_tz)
        
        time_str = city_time.strftime("%H:%M:%S")
        date_str = city_time.strftime("%d.%m.%Y")
        
        day_offset = ""
        if city_time.date() > home_time.date():
            day_offset = " (+1)"
        elif city_time.date() < home_time.date():
            day_offset = " (-1)"
            
        prefix = "*" if city["name"] == self.reference_location else ""
        
        display_str = f"{prefix}{city['name'].upper()}: {time_str} | {date_str}{day_offset}".lower()
        display_str = display_str.replace(city['name'].lower(), city['name'].upper())
        
        return display_str
