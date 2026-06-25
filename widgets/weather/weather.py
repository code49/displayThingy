import time
import threading
import requests

class WeatherWidget:
    def __init__(self, cities, api_poll_interval=300):
        self.cities = cities
        self.api_poll_interval = api_poll_interval
        self.weather_cache = {city: "loading..." for city in cities}
        self.last_sync_time = 0 # Force immediate fetch on start

    def update(self, current_time=None):
        if current_time is None:
            current_time = time.time()
            
        # Trigger background batch sync if interval has elapsed
        if current_time - self.last_sync_time > self.api_poll_interval:
            self.fetch_all_weather_async()
            self.last_sync_time = current_time

    def fetch_all_weather_async(self):
        """
        Spawns a single background thread to sequentially fetch weather for all cities.
        Sequential fetching with a tiny delay prevents rate-limiting.
        """
        def target():
            for city in self.cities:
                try:
                    url = f"https://wttr.in/{city}?format=j1"
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        cond = data['current_condition'][0]
                        
                        desc = cond['weatherDesc'][0]['value'].strip().lower()
                        
                        t_val = int(cond['temp_C'])
                        temp_sign = "+" if t_val > 0 else ""
                        temp = f"{temp_sign}{t_val}°C"
                        
                        wind_speed = f"{cond['windspeedKmph']}km/h"
                        wind_dir = cond['winddir16Point']
                        
                        weather_text = f"{desc} | {temp} {wind_speed} {wind_dir}"
                        self.weather_cache[city] = weather_text
                    else:
                        # Fallback to keep previous cached text if available
                        if self.weather_cache.get(city) == "loading...":
                            self.weather_cache[city] = f"error {response.status_code}"
                except Exception as e:
                    print(f"Error fetching weather for {city}: {e}")
                    if self.weather_cache.get(city) == "loading...":
                        self.weather_cache[city] = "query failed"
                
                # Polite delay between sequential requests to avoid hammering wttr.in
                time.sleep(0.5)

        thread = threading.Thread(target=target, daemon=True)
        thread.start()

    def get_weather(self, city_name, include_location=True):
        """
        Retrieves the cached weather string.
        """
        weather_text = self.weather_cache.get(city_name, "loading...")
        
        if include_location:
            return f"{city_name.upper()}: {weather_text}"
        return weather_text
