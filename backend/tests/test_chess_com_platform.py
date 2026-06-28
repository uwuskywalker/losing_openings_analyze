import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from platforms.chess_com import ChessComPlatform


class ChessComPlatformTests(unittest.TestCase):
    def test_fetch_games_returns_opening_details_for_frontend(self):
        platform = ChessComPlatform('testuser')

        archive_response = Mock()
        archive_response.json.return_value = {
            'archives': ['https://example.com/archive1']
        }

        games_response = Mock()
        games_response.json.return_value = {
            'games': [{
                'end_time': 1710000000,
                'white': {'username': 'testuser', 'rating': 1200, 'result': 'loss'},
                'black': {'username': 'other', 'rating': 1300, 'result': 'win'},
                'pgn': '[Event "Live Chess"]\n[ECO "B20"]\n[White "testuser"]\n[Black "other"]\n1. e4 e5 2. Nf3 Nc6',
                'eco': 'https://www.chess.com/openings/Sicilian-Defense',
                'time_class': 'rapid'
            }]
        }

        with patch('requests.get', side_effect=[archive_response, games_response]), \
             patch('psycopg2.connect') as mock_connect:
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = ('Sicilian Defense',)
            mock_connect.return_value.cursor.return_value = mock_cursor

            result = platform.fetch_games()

            self.assertEqual(result['recent_games'][0]['opening_name'], 'Sicilian Defense')
            self.assertEqual(result['recent_games'][0]['eco'], 'B20')
            self.assertEqual(result['top_blind_spots'][0]['eco'], 'B20')
            self.assertEqual(result['top_blind_spots'][0]['opening_name'], 'Sicilian Defense')


if __name__ == '__main__':
    unittest.main()
