import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Mock pygame before importing SpotifyDisplay
sys.modules['pygame'] = MagicMock()
import pygame

# Mock spotify module
sys.modules['spotify'] = MagicMock()
import spotify

from main import SpotifyDisplay

class TestErrorHandling(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        spotify.get_spotify_client.return_value = MagicMock()
        
        # Make font.size return a tuple (width, height)
        # We'll make it return a small width so it doesn't wrap too much in tests
        def mock_size(text):
            return (len(text) * 5, 20)
        
        pygame.font.SysFont.return_value.size.side_effect = mock_size
        
    def test_initialization(self):
        display = SpotifyDisplay(1024, 600)
        self.assertIsNone(display.error_message)
        self.assertIsNone(display.track_info)

    @patch('main.get_current_track_info')
    def test_run_loop_error_handling(self, mock_get_info):
        # Setup
        display = SpotifyDisplay(1024, 600)
        display.api_poll_interval = 0 # Force sync
        
        # Mock an error return
        mock_get_info.return_value = {"error": "Test Error Message"}
        
        # We need to simulate one iteration of the loop
        # We'll mock pygame.event.get to return a QUIT event after one loop
        pygame.event.get.side_effect = [[], [MagicMock(type=pygame.QUIT)]]
        
        # Run the loop
        display.run()
        
        # Verify error_message is set and track_info is None
        self.assertEqual(display.error_message, "Test Error Message")
        self.assertIsNone(display.track_info)

    @patch('main.get_current_track_info')
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
