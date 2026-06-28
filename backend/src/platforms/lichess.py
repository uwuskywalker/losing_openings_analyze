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
    def _parse(self, data):
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
        pgn_string = data.get("pgn") # 拿到 Lichess 包在 JSON 裡的 pgn 字串
        
        if pgn_string:
            try:
                # 使用 io.StringIO 把字串轉成檔案流，交給 chess.pgn 讀取
                pgn_file = io.StringIO(pgn_string)
                parsed_game = chess.pgn.read_game(pgn_file)
                
                if parsed_game:
                    # 提取出標準的走子順序（例如: "1. e4 e5 2. Nf3 Nc6..."）
                    # 這裡使用 main.line_moves() 可以拿到每一著，並串成標準記譜字串
                    moves = [move.uci() for move in parsed_game.mainline_moves()] # 拿到 UCI 格式 (例如 e2e4)
                    # 如果想要標準 SAN 格式 (例如 e4, Nf3)，可以用 parsed_game.mainline() 的印出
                    pgn_moves_str = str(parsed_game.mainline()) 
            except Exception as pgn_err:
                print(f"解析 PGN 失敗: {pgn_err}")
                pgn_moves_str = "棋譜解析錯誤"

        return {
            "username": self.username,
            "rating": data.get("players", {}).get(player_color, {}).get("rating"),
            "date": datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d') if created_at else "N/A",
            "result": result,
            "mode": data.get("speed"),
            "eco": data.get("opening", {}).get("eco"),
            "moves": pgn_moves_str
        }

    def fetch_games(self):
        # 1. 在網址加上 &pgnInJson=true，這樣 ndjson 裡就會包含 "pgn" 欄位
        url = f"https://lichess.org/api/games/user/{self.username}?max=100&pgnInJson=true"
        response = requests.get(url, headers={'Accept': 'application/x-ndjson'})
        lines = response.text.strip().split('\n')
        
        # 2. 跑你原本的解析邏輯，拿到 100 場基本資料
        games_list = [self._parse(json.loads(line)) for line in lines if line]
        
        # 3. 過濾出「輸局」的 ECO 代碼
        loss_ecos = [g["eco"] for g in games_list if g["result"] == "loss" and g.get("eco")]
        
        # 4. 計算最常輸的 ECO 前 5 名
        eco_counts = Counter(loss_ecos)
        top_5_ecos = eco_counts.most_common(5)
        
        # 5. 連線到 PostgreSQL 資料庫查開局名稱
        blind_spots = []
        try:
            conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT")
            )
            cursor = conn.cursor()
            
            for eco, count in top_5_ecos:
                cursor.execute("SELECT name FROM lichess_openings WHERE eco = %s LIMIT 1;", (eco,))
                result = cursor.fetchone()
                opening_name = result[0] if result else "未知開局"
                
                blind_spots.append({
                    "eco": eco,
                    "opening_name": opening_name,
                    "loss_count": count
                })
                
            cursor.close()
            conn.close()
        except Exception as db_err:
            print(f"資料庫連線或查詢失敗: {db_err}")
            # 如果資料庫爆了，提供基本的 ECO 資訊兜底，不讓整個網頁掛掉
            blind_spots = [{"eco": eco, "opening_name": "資料庫連線失敗", "loss_count": count} for eco, count in top_5_ecos]

        # 6. 回傳最終整合資料：包涵原本的 100 場紀錄，並塞入全新的盲點報告欄位！
        return {
            "player_info": {
                "username": self.username,
                "total_games_analyzed": len(games_list),
                "total_losses": len(loss_ecos)
            },
            "recent_games": games_list,      # 你原本前端要的 100 場陣列
            "top_blind_spots": blind_spots   # 新增的資料庫盲點分析報告
        }
    
    def get_opening_name(cursor, eco, moves_str):
    # 1. 優先嘗試用 ECO 代碼查詢
        if eco:
            cursor.execute("SELECT name FROM lichess_openings WHERE eco = %s LIMIT 1;", (eco.upper(),))
            result = cursor.fetchone()
            if result: return result[0]

        # 2. 如果 ECO 為空，則嘗試用 PGN 棋譜的前幾步進行模糊比對
        prefix_moves = " ".join(moves_str.split()[:6]) 
        
        # 使用 LIKE 模糊匹配資料庫中的開局走法欄位
        cursor.execute("SELECT name FROM lichess_openings WHERE moves LIKE %s LIMIT 1;", (f"{prefix_moves}%",))
        result = cursor.fetchone()
    
        return result[0] if result else "未知開局"