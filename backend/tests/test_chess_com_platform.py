import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from platforms.chess_com import ChessComPlatform


class ChessComPlatformTests(unittest.TestCase):
    def test_parse_treats_draw_results_as_draw(self):
        platform = ChessComPlatform('testuser')
        game_data = {
            'end_time': 1710000000,
            'white': {'username': 'testuser', 'rating': 1200},
            'black': {'username': 'other', 'rating': 1300},
            'pgn': '[Event "Live Chess"]\n[Site "Chess.com"]\n[Date "2024.03.08"]\n[Round "-"]\n[White "testuser"]\n[Black "other"]\n[Result "1/2-1/2"]\n1. e4 e5 1/2-1/2',
            'time_class': 'rapid'
        }

        parsed = platform._parse(game_data, None)

        self.assertEqual(parsed['result'], 'draw')

    def test_get_opening_name_prefers_move_sequence_match(self):
        platform = ChessComPlatform('testuser')
        cursor = Mock()
        cursor.fetchall.return_value = [('Sicilian Defense', '1. e4 c5 2. Nf3 d6')]

        result = platform.get_opening_name(cursor, 'B20', '[ECO "B20"]\n1. e4 c5 2. Nf3 d6')

        self.assertEqual(result, 'Sicilian Defense')

    def test_get_opening_name_prefers_general_opening_when_moves_match_earlier(self):
        platform = ChessComPlatform('testuser')
        cursor = Mock()
        cursor.fetchall.return_value = [
            ('Australian Defense', 'd4 g6 c4 Bg7 Nf3 d6 e4 e5'),
            ("Queen's Pawn Game: Modern Defense", 'd4 g6 c4 Bg7 Nf3 d6')
        ]

        result = platform.get_opening_name(cursor, 'A40', '[ECO "A40"]\n1. d4 g6 2. c4 Bg7 3. Nf3 d6 4. e4 e5 5. dxe5 dxe5 6. Qxd8+ Kxd8 7. Nc3 Nc6')

        self.assertEqual(result, "Queen's Pawn Game: Modern Defense")

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
