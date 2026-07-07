import hashlib
import io
import os
import re
import requests
import chess.pgn
from collections import Counter
from datetime import datetime

try:
    from .base import ChessPlatform
except ImportError:
    from base import ChessPlatform

try:
    from db import get_db_connection, ensure_game_analysis_table, save_game_analysis, fetch_stored_games
except ImportError:
    from ..db import get_db_connection, ensure_game_analysis_table, save_game_analysis, fetch_stored_games


class ChessComPlatform(ChessPlatform):
    HEADERS = {'User-Agent': 'ChessFetcherApp'}

    def _normalize_result(self, raw_result, pgn_str=None, user_color=None):
        if raw_result is None:
            raw_result = None
        elif isinstance(raw_result, str):
            raw_result = raw_result.strip().lower()

        if raw_result in {"win", "won", "w"}:
            return "win" if user_color != "black" else "loss"
        if raw_result in {"draw", "drawn", "agreed", "stalemate", "repetition", "insufficient", "fifty-move", "seventy-five-move", "half-point"}:
            return "draw"
        if raw_result in {"loss", "lose", "lost", "l"}:
            return "loss" if user_color != "black" else "win"
        if raw_result in {"white", "1-0"}:
            return "win" if user_color == "white" else "loss"
        if raw_result in {"black", "0-1"}:
            return "win" if user_color == "black" else "loss"
        if raw_result in {"1/2-1/2"}:
            return "draw"

        if pgn_str:
            match = re.search(r'\[Result\s+"([^"]+)"\]', pgn_str)
            if match:
                return self._normalize_result(match.group(1), None, user_color)

            if "1/2-1/2" in pgn_str:
                return "draw"
            if "1-0" in pgn_str:
                return "win" if user_color == "white" else "loss"
            if "0-1" in pgn_str:
                return "win" if user_color == "black" else "loss"

        return None

    def _parse(self, data, cursor):
        end_time = data.get("end_time", 0)
        user_color = "white" if data.get("white", {}).get("username", "").lower() == self.username.lower() else "black"
        player_data = data.get(user_color, {})
        pgn_str = data.get("pgn", "")
        raw_eco = data.get("eco")
        eco_code = self.get_eco_code(raw_eco, pgn_str)
        raw_result = player_data.get("result")
        if raw_result is None:
            raw_result = data.get("result")

        result = self._normalize_result(raw_result, pgn_str, user_color)
        if result is None:
            result = "loss"

        opening_name = self.get_opening_name(cursor, eco_code, pgn_str)
        played_at = datetime.fromtimestamp(end_time).date() if end_time else None

        return {
            "source": "chess.com",
            "username": self.username,
            "game_id": self._get_game_id(data),
            "played_at": played_at,
            "rating": player_data.get("rating"),
            "date": played_at.isoformat() if played_at else "N/A",
            "result": result,
            "mode": data.get("time_class"),
            "eco": eco_code or "N/A",
            "opening_name": opening_name,
            "moves": pgn_str,
        }

    def get_eco_code(self, raw_eco, pgn_str):
        if raw_eco:
            raw_eco_str = str(raw_eco).strip()
            if raw_eco_str.startswith("http"):
                match = re.search(r'/openings/([^/]+)$', raw_eco_str)
                if match:
                    return self._extract_eco_from_pgn(pgn_str)
                return self._extract_eco_from_pgn(pgn_str)
            return raw_eco_str

        return self._extract_eco_from_pgn(pgn_str)

    def _extract_eco_from_pgn(self, pgn_str):
        if not pgn_str:
            return None
        match = re.search(r'\[ECO\s+"([A-Z][0-9]{2})"\]', pgn_str)
        if match:
            return match.group(1).upper()
        return None

    def _normalize_opening_text(self, text):
        if not text:
            return ""
        text = str(text).lower()
        text = re.sub(r'\[.*?\]', ' ', text)
        text = re.sub(r'\d+\.', ' ', text)
        text = re.sub(r'[^a-z0-9]+', ' ', text).strip()
        return text

    def _score_opening_candidate(self, actual_moves, candidate_moves, prefix_length=6):
        actual_tokens = self._normalize_opening_text(actual_moves).split()
        candidate_tokens = self._normalize_opening_text(candidate_moves).split()
        if not actual_tokens or not candidate_tokens:
            return (-1, -1, -1, -1)

        def matched_count(limit):
            matched = 0
            for index in range(min(limit, len(actual_tokens), len(candidate_tokens))):
                if actual_tokens[index] == candidate_tokens[index]:
                    matched += 1
                else:
                    break
            return matched

        primary_matches = matched_count(4)
        secondary_matches = matched_count(min(6, prefix_length))
        tertiary_matches = matched_count(prefix_length)
        return (primary_matches, secondary_matches, tertiary_matches, -len(candidate_tokens))

    def _get_opening_candidates(self, cursor, eco):
        if cursor is None or not eco or eco == "N/A":
            return []

        try:
            cursor.execute("SELECT name, pgn FROM lichess_openings WHERE eco = %s;", (str(eco).upper(),))
            rows = cursor.fetchall()
            if rows:
                return list(rows)
        except Exception:
            pass

        try:
            cursor.execute("SELECT name FROM lichess_openings WHERE eco = %s LIMIT 1;", (str(eco).upper(),))
            result = cursor.fetchone()
            if result:
                return [(result[0], "")]
        except Exception:
            pass

        return []

    def get_opening_name(self, cursor, eco, pgn_str):
        if cursor is None:
            return "未知開局"

        candidates = self._get_opening_candidates(cursor, eco)
        if candidates:
            if pgn_str:
                moves = self._extract_move_sequence(pgn_str)
                prefix_moves = " ".join(moves[:14]).strip()
                if prefix_moves:
                    best_name = None
                    best_score = None

                    for prefix_length in [6, 8, 10, 12, 14, 4, 2]:
                        prefix_slice = " ".join(moves[:prefix_length]).strip()
                        if not prefix_slice:
                            continue

                        best_name = None
                        best_score = None
                        for name, opening_pgn in candidates:
                            score = self._score_opening_candidate(prefix_slice, opening_pgn, prefix_length)
                            if not best_score or score > best_score:
                                best_score = score
                                best_name = name

                        if best_name and best_score and best_score[0] > 0:
                            return best_name

                    if best_name:
                        return best_name

            first_name = candidates[0][0] if candidates[0] else None
            if first_name:
                return first_name

        if pgn_str:
            moves = self._extract_move_sequence(pgn_str)
            query_str = " ".join(moves[:6]).strip()

            if query_str:
                try:
                    cursor.execute("SELECT name FROM lichess_openings WHERE pgn LIKE %s LIMIT 1;", (f"%{query_str}%",))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
                except Exception:
                    pass

        return "未知開局"

    def _extract_move_sequence(self, pgn_str):
        if not pgn_str:
            return []

        try:
            pgn_io = io.StringIO(pgn_str)
            game = chess.pgn.read_game(pgn_io)
            if not game:
                return []

            moves = []
            node = game
            while node.variations:
                next_node = node.variations[0]
                san = next_node.san()
                moves.append(san)
                node = next_node
            return moves
        except Exception:
            clean_pgn = re.sub(r'\[.*?\]', '', pgn_str)
            clean_pgn = re.sub(r'\d+\.', '', clean_pgn)
            return re.findall(r'[a-zA-Z0-9+#]+', clean_pgn)

    def _get_game_id(self, data):
        if not data:
            return None
        game_id = data.get('url') or data.get('game_id') or data.get('id') or data.get('uuid')
        if game_id:
            return str(game_id)
        pgn_str = data.get('pgn', '')
        return hashlib.sha1(pgn_str.encode('utf-8')).hexdigest() if pgn_str else None

    def fetch_games(self):
        archives_url = f"https://api.chess.com/pub/player/{self.username}/games/archives"
        try:
            res = requests.get(archives_url, headers=self.HEADERS).json()
            all_archives = res.get('archives', [])[-5:]

            all_games = []
            for url in all_archives:
                month_data = requests.get(url, headers=self.HEADERS).json().get('games', [])
                all_games.extend(month_data)
        except Exception as e:
            print(f"Chess.com API 請求失敗: {e}")
            return {"player_info": {}, "recent_games": [], "top_blind_spots": []}

        conn = None
        cursor = None
        games_list = []

        try:
            conn = get_db_connection()
            ensure_game_analysis_table(conn)
            cursor = conn.cursor()

            games_list = [self._parse(game_data, cursor) for game_data in all_games[::-1]]
            save_game_analysis(conn, games_list)
            games_list = fetch_stored_games(conn, 'chess.com', self.username)
        except Exception as db_err:
            print(f"資料庫處理失敗: {db_err}")
            if not games_list:
                games_list = [self._parse(game_data, None) for game_data in all_games[::-1]]
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

        loss_openings = [g["opening_name"] for g in games_list if g["result"] == "loss" and g.get("opening_name")]
        if not loss_openings:
            loss_openings = [g["opening_name"] for g in games_list if g.get("opening_name")]

        opening_counts = Counter(loss_openings)
        top_blind_spots = []
        for name, count in opening_counts.most_common(5):
            eco = "N/A"
            for game in games_list:
                if game.get("opening_name") == name and game.get("result") == "loss" and game.get("eco") not in (None, "N/A"):
                    eco = game.get("eco")
                    break
            top_blind_spots.append({"eco": eco, "opening_name": name, "loss_count": count})

        return {
            "player_info": {"username": self.username, "total_games_analyzed": len(games_list), "total_losses": len([g for g in games_list if g["result"] == "loss"])},
            "recent_games": games_list,
            "top_blind_spots": top_blind_spots,
        }