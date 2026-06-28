import requests
from datetime import datetime
from .base import ChessPlatform

class ChessComPlatform(ChessPlatform):
    HEADERS = {'User-Agent': 'ChessFetcherApp'}

    def _parse(self, data):
        end_time = data.get("end_time", 0)
        user_color = "white" if data.get("white", {}).get("username") == self.username else "black"
        player_data = data.get(user_color, {})
        
        return {
            "username": self.username,
            "rating": player_data.get("rating"),
            "date": datetime.fromtimestamp(end_time).strftime('%Y-%m-%d') if end_time else "N/A",
            "result": "win" if player_data.get("result") == "win" else "loss",
            "mode": data.get("time_class")
        }

    def fetch_games(self):
        archives_url = f"https://api.chess.com/pub/player/{self.username}/games/archives"
        res = requests.get(archives_url, headers=self.HEADERS).json()
        all_archives = res.get('archives', [])
        recent_months = all_archives[-5:]
        
        all_games = []
        for url in recent_months:
            month_data = requests.get(url, headers=self.HEADERS).json().get('games', [])
            all_games.extend(month_data)
            
        return [self._parse(g) for g in all_games[::-1]]