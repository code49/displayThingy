'''
Script that pulls down the current state of the '88' playlist
and makes a plot of (first) artists.
'''


import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import matplotlib.pyplot as plt

# Load variables from .env into the environment
load_dotenv()

# os.getenv looks for the keys defined in your .env file
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv('SPOTIPY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
    redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
    scope="playlist-read-private",
    show_dialog=True
))

my_playlist_id = '4soTsWdI5kIAxa9kACgJb4'

# Instead of playlist_items(), we just request the entire playlist
playlist_data = sp.playlist(
    playlist_id=my_playlist_id,
    market='US',
    # additional_types=('track',)
)

# Assuming you used the sp.playlist() workaround
tracks = playlist_data['items']['items']

print(f"Success! Retrieved {len(tracks)} tracks directly from the playlist metadata.")

# 2. Create an empty list to hold the flattened data
track_list = []

# 3. Loop through each item to extract the relevant fields
for item in tracks:
    # # Safely get the track data (handling varying API response structures)
    track = item['item']
    
    # Append a dictionary representing a single row of data
    entry = {
        'name': track['name'],
        'artist': [artist['name'] for artist in track['artists']][0],
        'album': track['album']['name'],
        # 'Track ID': track.get('id'),
        # 'Popularity': track.get('popularity'),
        # 'Duration (ms)': track.get('duration_ms')
    }

    track_list.append(entry)

# 4. Convert the flat list into a pandas DataFrame
df = pd.DataFrame(track_list)
print(df.head())

# ------------------------------------------------------
artist_counts = df['artist'].explode().value_counts()

print(artist_counts)

top_n = 18
if len(artist_counts) > top_n:
    top_artists = artist_counts[:top_n]
    other_count = artist_counts[top_n:].sum()
    # Create a new series for the plot
    plot_data = top_artists._append(pd.Series({'Other': other_count}))
else:
    plot_data = artist_counts

# 3. Create the pie chart
plt.pie(
    plot_data, 
    labels=plot_data.index, 
    autopct='%1.1f%%',   # Shows the percentage on the slice
    startangle=140,      # Rotates the start for better aesthetics
    colors=plt.cm.Paired.colors # Uses a nice color palette
)

plt.title('Artist Distribution in My Playlist')
plt.axis('equal')
plt.savefig('spotify_artist_distribution.png')
