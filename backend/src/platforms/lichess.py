import requests
import json
from datetime import datetime
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
        return {
            "username": self.username,
            "rating": data.get("players", {}).get(player_color, {}).get("rating"),
            "date": datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d') if created_at else "N/A",
            "result": result,
            "mode": data.get("speed")
        }

    def fetch_games(self):
        url = f"https://lichess.org/api/games/user/{self.username}?max=100"
        response = requests.get(url, headers={'Accept': 'application/x-ndjson'})
        lines = response.text.strip().split('\n')
        return [self._parse(json.loads(line)) for line in lines if line]