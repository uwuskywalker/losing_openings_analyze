import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from platforms.lichess import LichessPlatform


class LichessPlatformTests(unittest.TestCase):
    def test_parse_uses_api_opening_name_when_available(self):
        platform = LichessPlatform('testuser')
        game_data = {
            'players': {
                'white': {'user': {'id': 'testuser'}, 'rating': 1200},
                'black': {'user': {'id': 'other'}, 'rating': 1300},
            },
            'winner': None,
            'createdAt': 1710000000,
            'pgn': '[Event "Live Chess"]\n[ECO "B20"]\n1. e4 c5 2. Nf3 d6',
            'opening': {'eco': 'B20', 'name': 'Sicilian Defense'}
        }

        cursor = Mock()
        parsed = platform._parse(game_data, cursor)

        self.assertEqual(parsed['opening_name'], 'Sicilian Defense')

    def test_parse_uses_player_color_for_result(self):
        platform = LichessPlatform('testuser')
        game_data = {
            'players': {
                'white': {'user': {'id': 'other'}, 'rating': 1200},
                'black': {'user': {'id': 'testuser'}, 'rating': 1300},
            },
            'winner': 'white',
            'createdAt': 1710000000,
            'pgn': '[Event "Live Chess"]\n[Result "1-0"]\n1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0'
        }

        parsed = platform._parse(game_data, None)

        self.assertEqual(parsed['result'], 'loss')

    def test_fetch_games_uses_cursor_after_db_connection(self):
        platform = LichessPlatform('testuser')

        fake_response = Mock()
        fake_response.text = '{"id":"1","winner":"black","players":{"white":{"user":{"id":"testuser"},"rating":1200},"black":{"user":{"id":"other"},"rating":1300}},"createdAt": 1710000000000, "pgn": "1. e4 e5 2. Nf3 Nc6"}\n'

        with patch('requests.get', return_value=fake_response), \
             patch('psycopg2.connect') as mock_connect:
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = ('Sicilian Defense',)
            mock_cursor.fetchall.return_value = [('game123', None, 1200, 'loss', 'rapid', 'B20', 'Sicilian Defense', '1. e4 e5 2. Nf3 Nc6')]
            mock_connect.return_value.cursor.return_value = mock_cursor

            result = platform.fetch_games()

            self.assertEqual(result['player_info']['username'], 'testuser')
            self.assertEqual(result['recent_games'][0]['eco'], 'B20')
            self.assertEqual(result['top_blind_spots'][0]['opening_name'], 'Sicilian Defense')


if __name__ == '__main__':
    unittest.main()
