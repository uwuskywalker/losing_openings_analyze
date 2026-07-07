import hashlib
import requests
import json
import re
import chess.pgn
import io
import os
from datetime import datetime
from collections import Counter

try:
    from .base import ChessPlatform
except ImportError:
    from base import ChessPlatform

try:
    from db import get_db_connection, ensure_game_analysis_table, save_game_analysis, fetch_stored_games
except ImportError:
    from ..db import get_db_connection, ensure_game_analysis_table, save_game_analysis, fetch_stored_games

class LichessPlatform(ChessPlatform):
    def _normalize_result(self, raw_result, player_color=None, pgn_str=None):
        if raw_result is None:
            return "draw"
        if isinstance(raw_result, str):
            raw_result = raw_result.strip().lower()

        if raw_result in {"win", "won", "white", "1-0", "w"}:
            return "win" if player_color == "white" else "loss"
        if raw_result in {"draw", "drawn", "1/2-1/2", "agreed", "stalemate", "repetition", "insufficient", "fifty-move", "seventy-five-move", "half-point"}:
            return "draw"
        if raw_result in {"loss", "lose", "lost", "black", "0-1", "l"}:
            return "loss" if player_color == "white" else "win"

        if pgn_str:
            match = re.search(r'\[Result\s+"([^"]+)"\]', pgn_str)
            if match:
                return self._normalize_result(match.group(1), player_color, None)
            if "1/2-1/2" in pgn_str:
                return "draw"
            if "1-0" in pgn_str:
                return "win" if player_color == "white" else "loss"
            if "0-1" in pgn_str:
                return "win" if player_color == "black" else "loss"

        return "draw"

    def _parse(self, data, cursor=None):
        winner = data.get("winner")
        player_color = "white" if data.get("players", {}).get("white", {}).get("user", {}).get("id") == self.username.lower() else "black"

        pgn_string = data.get("pgn", "") or ""
        if winner is None:
            result = self._normalize_result(None, player_color, pgn_string)
        else:
            result = self._normalize_result(winner, player_color, pgn_string)

        created_at = data.get("createdAt", 0)
        opening_data = data.get("opening") or {}
        eco_code = self.get_eco_code(opening_data.get("eco"), pgn_string)
        opening_name = opening_data.get("name") or self.get_opening_name(cursor, eco_code, pgn_string)

        played_at = datetime.fromtimestamp(created_at / 1000).date() if created_at else None

        return {
            "source": "lichess",
            "username": self.username,
            "game_id": self._get_game_id(data),
            "played_at": played_at,
            "rating": data.get("players", {}).get(player_color, {}).get("rating"),
            "date": played_at.isoformat() if played_at else "N/A",
            "result": result,
            "mode": data.get("speed"),
            "eco": eco_code or "N/A",
            "opening_name": opening_name,
            "moves": pgn_string
        }

    def _get_game_id(self, data):
        if not data:
            return None
        game_id = data.get('id') or data.get('game_id') or data.get('url') or data.get('uuid')
        if game_id:
            return str(game_id)
        pgn_str = data.get('pgn', '')
        return hashlib.sha1(pgn_str.encode('utf-8')).hexdigest() if pgn_str else None

    def fetch_games(self):
        url = f"https://lichess.org/api/games/user/{self.username}?max=100&pgnInJson=true"
        response = requests.get(url, headers={"Accept": "application/x-ndjson"})
        lines = [line for line in response.text.splitlines() if line.strip()]
        parsed_games = [json.loads(line) for line in lines]

        conn = None
        cursor = None
        games_list = []
        blind_spots = []

        try:
            conn = get_db_connection()
            ensure_game_analysis_table(conn)
            cursor = conn.cursor()

            games_list = [self._parse(game_data, cursor) for game_data in parsed_games]
            save_game_analysis(conn, games_list)
            games_list = fetch_stored_games(conn, 'lichess', self.username)
        except Exception as db_err:
            print(f"資料庫處理失敗: {db_err}")
            if not games_list:
                games_list = [self._parse(game_data, None) for game_data in parsed_games]
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

        loss_openings = [g["opening_name"] for g in games_list if g["result"] == "loss" and g.get("opening_name")]
        if not loss_openings:
            loss_openings = [g["opening_name"] for g in games_list if g.get("opening_name")]

        opening_counts = Counter(loss_openings)
        for name, count in opening_counts.most_common():
            eco_code = "N/A"
            for game in games_list:
                if game.get("opening_name") == name and game.get("eco") not in (None, "N/A"):
                    eco_code = game.get("eco")
                    break

            blind_spots.append({
                "eco": eco_code,
                "opening_name": name,
                "loss_count": count
            })

        return {
            "player_info": {
                "username": self.username,
                "total_games_analyzed": len(games_list),
                "total_losses": len([g for g in games_list if g["result"] == "loss"])
            },
            "recent_games": games_list,
            "top_blind_spots": blind_spots
        }

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
            try:
                moves = self._extract_move_sequence(pgn_str)
                if moves:
                    prefix_moves = " ".join(moves[:6])
                    cursor.execute("SELECT name FROM lichess_openings WHERE pgn LIKE %s LIMIT 1;", (f"{prefix_moves}%",))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
            except Exception as e:
                print(f"PGN 查詢過程中發生錯誤: {e}")

        return "未知開局"

    def get_eco_code(self, raw_eco, pgn_str):
        if raw_eco:
            raw_eco_str = str(raw_eco).strip()
            if raw_eco_str.startswith("http"):
                return self._extract_eco_from_pgn(pgn_str)
            return raw_eco_str.upper()

        return self._extract_eco_from_pgn(pgn_str)

    def _extract_eco_from_pgn(self, pgn_str):
        if not pgn_str:
            return None

        match = re.search(r'\[ECO\s+"([A-Z][0-9]{2})"\]', pgn_str)
        return match.group(1).upper() if match else None

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
                node = node.variations[0]
                moves.append(node.san())
            return moves
        except Exception:
            clean_pgn = re.sub(r'\[.*?\]', '', pgn_str)
            clean_pgn = re.sub(r'\d+\.', '', pgn_str)
            return re.findall(r'[a-zA-Z0-9+#]+', clean_pgn)
