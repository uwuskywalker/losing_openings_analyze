import requests
import os
import psycopg2
from datetime import datetime
from .base import ChessPlatform

class ChessComPlatform(ChessPlatform):
    HEADERS = {'User-Agent': 'ChessFetcherApp'}

    def _parse(self, data, cursor):
        end_time = data.get("end_time", 0)
        user_color = "white" if data.get("white", {}).get("username") == self.username else "black"
        player_data = data.get(user_color, {})
        pgn_str = data.get("pgn", "")
        raw_eco = data.get("eco", None)
        opening_name = self.get_opening_name(cursor, None, pgn_str)
        
        # 嘗試從資料庫或 PGN 計算開局名稱
        # 注意：Chess.com 的 PGN 字串比較長，可能需要處理格式
        opening_name = self.get_opening_name(cursor, None, pgn_str)
        
        return {
            "username": self.username,
            "rating": player_data.get("rating"),
            "date": datetime.fromtimestamp(end_time).strftime('%Y-%m-%d') if end_time else "N/A",
            "result": "win" if player_data.get("result") == "win" else "loss",
            "mode": data.get("time_class"),
            "eco": raw_eco if raw_eco else "N/A",
            "opening_name": opening_name, # 我們直接存開局名稱
            "moves": pgn_str
        }
    def get_opening_name(self, cursor, eco, pgn_str):
        import re
        
        # 1. 移除標頭並只保留棋步 (去除所有數字和點)
        clean_pgn = re.sub(r'\[.*?\]', '', pgn_str)
        # 移除數字和點 (例如 '1. e4' -> ' e4')
        clean_pgn = re.sub(r'\d+\.', '', clean_pgn)
        
        # 2. 提取所有單字 (棋步)
        moves = re.findall(r'[a-zA-Z0-9+#]+', clean_pgn)
        
        # 3. 過濾掉垃圾詞彙
        valid_moves = [m for m in moves if m not in ['Event', 'Live', 'Chess', 'Site', 'com', 'UTC', 'Result', 'White', 'Black']]
        
        # 4. 只取前 4 個棋步進行比對 (對應 '%e4 c5%')
        query_str = " ".join(valid_moves[:4])
        
        print(f"DEBUG: 最終比對字串: '{query_str}'")
        
        try:
            # 使用 % 包圍，確保模糊匹配
            cursor.execute("SELECT name FROM lichess_openings WHERE pgn LIKE %s LIMIT 1;", (f"%{query_str}%",))
            result = cursor.fetchone()
            
            return result[0] if result else "未知開局"
        except Exception as e:
            return "未知開局"
        
    def fetch_games(self):
        archives_url = f"https://api.chess.com/pub/player/{self.username}/games/archives"
        try:
            res = requests.get(archives_url, headers=self.HEADERS).json()
            all_archives = res.get('archives', [])[-5:] # 最近 5 個月
            
            all_games = []
            for url in all_archives:
                month_data = requests.get(url, headers=self.HEADERS).json().get('games', [])
                all_games.extend(month_data)
        except Exception as e:
            print(f"Chess.com API 請求失敗: {e}")
            return {"player_info": {}, "recent_games": [], "top_blind_spots": []}

        # 資料庫連線
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 5432))
        )
        cursor = conn.cursor()
        
        # 解析並取得遊戲紀錄
        games_list = [self._parse(g, cursor) for g in all_games[::-1]]
        
        # 統計盲點 (開局名稱為未知開局或特定敗場)
        # 這裡簡化為統計該用戶最常輸掉的開局名稱
        loss_openings = [g["opening_name"] for g in games_list if g["result"] == "loss"]
        from collections import Counter
        top_blind_spots = [{"opening_name": name, "loss_count": count} 
        for name, count in Counter(loss_openings).most_common(5)]
        
        cursor.close()
        conn.close()
        
        return {
            "player_info": {"username": self.username, "total_games_analyzed": len(games_list)},
            "recent_games": games_list,
            "top_blind_spots": top_blind_spots
        }