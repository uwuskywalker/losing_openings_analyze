import requests
import json
import chess.pgn
import io
import psycopg2
import os
from datetime import datetime
from collections import Counter
from .base import ChessPlatform

class LichessPlatform(ChessPlatform):
    def _parse(self, data, cursor=None):
        winner = data.get("winner")
        player_color = "white" if data.get("players", {}).get("white", {}).get("user", {}).get("id") == self.username.lower() else "black"

        if winner is None:
            result = "draw"
        elif winner == player_color:
            result = "win"
        else:
            result = "loss"

        created_at = data.get("createdAt", 0)

        pgn_moves_str = ""
        pgn_string = data.get("pgn")

        if pgn_string:
            try:
                pgn_file = io.StringIO(pgn_string)
                parsed_game = chess.pgn.read_game(pgn_file)

                if parsed_game:
                    pgn_moves_str = str(parsed_game.mainline())
            except Exception as pgn_err:
                print(f"解析 PGN 失敗: {pgn_err}")
                pgn_moves_str = "棋譜解析錯誤"

        raw_eco = data.get("opening", {}).get("eco")
        final_eco = raw_eco

        if not final_eco and cursor is not None:
            final_eco = self.get_opening_name(cursor, None, pgn_moves_str)

        if not final_eco:
            final_eco = "N/A"

        return {
            "username": self.username,
            "rating": data.get("players", {}).get(player_color, {}).get("rating"),
            "date": datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d') if created_at else "N/A",
            "result": result,
            "mode": data.get("speed"),
            "eco": final_eco,
            "moves": pgn_moves_str
        }

    def fetch_games(self):
        url = f"https://lichess.org/api/games/user/{self.username}?max=100&pgnInJson=true"
        response = requests.get(url, headers={'Accept': 'application/x-ndjson'})
        lines = [line for line in response.text.splitlines() if line.strip()]
        parsed_games = [json.loads(line) for line in lines]

        db_cursor = None
        games_list = []
        blind_spots = []

        try:
            db_port = os.getenv("DB_PORT", "5432")
            if db_port and db_port.startswith("="):
                db_port = db_port[1:]
            port = int(db_port) if str(db_port).isdigit() else 5432

            conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=port
            )
            db_cursor = conn.cursor()
        except Exception as db_err:
            print(f"資料庫連線失敗: {db_err}")

        games_list = [self._parse(game_data, db_cursor) for game_data in parsed_games]

        loss_ecos = [g["eco"] for g in games_list if g["result"] == "loss" and g.get("eco")]
        eco_counts = Counter(loss_ecos)
        top_5_ecos = eco_counts.most_common(5)

        if db_cursor is not None:
            try:
                for eco, count in top_5_ecos:
                    db_cursor.execute("SELECT name FROM lichess_openings WHERE eco = %s LIMIT 1;", (eco,))
                    result = db_cursor.fetchone()
                    opening_name = result[0] if result else "未知開局"

                    blind_spots.append({
                        "eco": eco,
                        "opening_name": opening_name,
                        "loss_count": count
                    })

                db_cursor.close()
            except Exception as db_err:
                print(f"資料庫查詢失敗: {db_err}")
                blind_spots = [{"eco": eco, "opening_name": "資料庫查詢失敗", "loss_count": count} for eco, count in top_5_ecos]
        else:
            blind_spots = [{"eco": eco, "opening_name": "資料庫連線失敗", "loss_count": count} for eco, count in top_5_ecos]

        return {
            "player_info": {
                "username": self.username,
                "total_games_analyzed": len(games_list),
                "total_losses": len(loss_ecos)
            },
            "recent_games": games_list,
            "top_blind_spots": blind_spots
        }

    def get_opening_name(self, cursor, eco, moves_str):
        if eco and eco != "N/A":
            try:
                cursor.execute("SELECT name FROM lichess_openings WHERE eco = %s LIMIT 1;", (eco.upper(),))
                result = cursor.fetchone()
                if result:
                    return result[0]
            except Exception:
                pass

        if moves_str and isinstance(moves_str, str) and len(moves_str) > 0:
            try:
                parts = moves_str.split()
                if parts:
                    prefix_moves = " ".join(parts[:6])
                    cursor.execute("SELECT name FROM lichess_openings WHERE pgn LIKE %s LIMIT 1;", (f"{prefix_moves}%",))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
            except Exception as e:
                print(f"PGN 查詢過程中發生錯誤: {e}")

        return "未知開局"