import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from platforms.lichess import LichessPlatform


class LichessPlatformTests(unittest.TestCase):
    def test_fetch_games_uses_cursor_after_db_connection(self):
        platform = LichessPlatform('testuser')

        fake_response = Mock()
        fake_response.text = '{"id":"1","winner":"black","players":{"white":{"user":{"id":"testuser"},"rating":1200},"black":{"user":{"id":"other"},"rating":1300}},"createdAt": 1710000000000, "pgn": "1. e4 e5 2. Nf3 Nc6"}\n'

        with patch('requests.get', return_value=fake_response), \
             patch('psycopg2.connect') as mock_connect:
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = ('Sicilian Defense',)
            mock_connect.return_value.cursor.return_value = mock_cursor

            result = platform.fetch_games()

            self.assertEqual(result['player_info']['username'], 'testuser')
            self.assertEqual(result['recent_games'][0]['eco'], 'Sicilian Defense')
            self.assertEqual(result['top_blind_spots'][0]['opening_name'], 'Sicilian Defense')


if __name__ == '__main__':
    unittest.main()
