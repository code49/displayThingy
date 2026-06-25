import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock pygame before importing SpotifyDisplay
sys.modules['pygame'] = MagicMock()
import pygame

# Import SpotifyDisplay
from main import SpotifyDisplay

class TestErrorHandling(unittest.TestCase):
    def setUp(self):
        # Patch get_spotify_client so it doesn't initialize real spotipy/OAuth client
        self.get_client_patcher = patch('widgets.spotify.spotify.get_spotify_client')
        self.mock_get_client = self.get_client_patcher.start()
        self.mock_get_client.return_value = MagicMock()
        
        # Make font.size return a tuple (width, height)
        def mock_size(text):
            return (len(text) * 5, 20)
        
        pygame.font.SysFont.return_value.size.side_effect = mock_size

    def tearDown(self):
        self.get_client_patcher.stop()
        
    def test_initialization(self):
        display = SpotifyDisplay(1024, 600)
        self.assertIsNone(display.error_message)
        self.assertIsNone(display.track_info)

    @patch('widgets.spotify.spotify.get_current_track_info')
    def test_run_loop_error_handling(self, mock_get_info):
        # Setup
        display = SpotifyDisplay(1024, 600)
        display.api_poll_interval = 0 # Force sync
        
        # Mock an error return
        mock_get_info.return_value = {"error": "Test Error Message"}
        
        # We need to simulate one iteration of the loop
        pygame.event.get.side_effect = [[], [MagicMock(type=pygame.QUIT)]]
        
        # Run the loop
        display.run()
        
        # Verify error_message is set and track_info is None
        self.assertEqual(display.error_message, "Test Error Message")
        self.assertIsNone(display.track_info)

    @patch('widgets.spotify.spotify.get_current_track_info')
    def test_test_error_flag(self, mock_get_info):
        display = SpotifyDisplay(1024, 600)
        display.api_poll_interval = 0
        
        pygame.event.get.side_effect = [[], [MagicMock(type=pygame.QUIT)]]
        
        # Run with test_error=True
        display.run(test_error=True)
        
        # Should set simulated error
        self.assertEqual(display.error_message, "Simulated API Error for testing")
        self.assertIsNone(display.track_info)
        # Should NOT have called real get_current_track_info
        mock_get_info.assert_not_called()

if __name__ == '__main__':
    unittest.main()
