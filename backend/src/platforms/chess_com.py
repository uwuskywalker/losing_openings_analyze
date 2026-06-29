import io
import os
import re
import psycopg2
import requests
import chess.pgn
from collections import Counter
from datetime import datetime

try:
    from .base import ChessPlatform
except ImportError:  # pragma: no cover - 支援直接執行檔案
    from base import ChessPlatform


class ChessComPlatform(ChessPlatform):
    HEADERS = {'User-Agent': 'ChessFetcherApp'}

    def _normalize_result(self, raw_result, pgn_str=None):
        if raw_result is None:
            raw_result = None
        elif isinstance(raw_result, str):
            raw_result = raw_result.strip().lower()

        if raw_result in {"win", "won", "white", "1-0", "w"}:
            return "win"
        if raw_result in {"draw", "drawn", "1/2-1/2", "agreed", "stalemate", "repetition", "insufficient", "fifty-move", "seventy-five-move", "half-point"}:
            return "draw"
        if raw_result in {"loss", "lose", "lost", "black", "0-1", "l"}:
            return "loss"

        if pgn_str:
            match = re.search(r'\[Result\s+"([^"]+)"\]', pgn_str)
            if match:
                return self._normalize_result(match.group(1), None)

            if "1/2-1/2" in pgn_str:
                return "draw"
            if "1-0" in pgn_str:
                return "win"
            if "0-1" in pgn_str:
                return "loss"

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

        result = self._normalize_result(raw_result, pgn_str)
        if result is None:
            result = "loss"

        opening_name = self.get_opening_name(cursor, eco_code, pgn_str)

        return {
            "username": self.username,
            "rating": player_data.get("rating"),
            "date": datetime.fromtimestamp(end_time).strftime('%Y-%m-%d') if end_time else "N/A",
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

    def get_opening_name(self, cursor, eco, pgn_str):
        if cursor is None:
            return "未知開局"

        if eco and eco != "N/A":
            try:
                cursor.execute("SELECT name FROM lichess_openings WHERE eco = %s LIMIT 1;", (str(eco).upper(),))
                result = cursor.fetchone()
                if result:
                    return result[0]
            except Exception:
                pass

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

        cursor = None
        conn = None
        try:
            db_port = os.getenv("DB_PORT", "5432")
            if str(db_port).startswith("="):
                db_port = db_port[1:]
            port = int(db_port) if str(db_port).isdigit() else 5432

            conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=port,
            )
            cursor = conn.cursor()
        except Exception as db_err:
            print(f"資料庫連線失敗: {db_err}")

        games_list = [self._parse(g, cursor) for g in all_games[::-1]]

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

        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

        return {
            "player_info": {"username": self.username, "total_games_analyzed": len(games_list)},
            "recent_games": games_list,
            "top_blind_spots": top_blind_spots,
        }