from flask import Flask, request, jsonify
from datetime import datetime
import requests
import json

app = Flask(__name__)

def parse_chess_com(data, username):
    # Chess.com 的架構通常需要先獲取 archives 列表，這裡簡化處理
    # 你需要先從 archives 取最後一個月，再抓該月資料
    # 這裡假設已經取得單場比賽的詳細物件
    end_time = data.get("end_time", 0)
    date_str = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d') if end_time else "N/A"
    return {
        "username": username,
        "rating": data.get("white" if data["white"]["username"] == username else "black", {}).get("rating"),
        "date": datetime.fromtimestamp(data.get("end_time", 0)).strftime('%Y-%m-%d'),
        "result": "win" if data[("white" if data["white"]["username"] == username else "black")]["result"] == "win" else "loss",
        "mode": data.get("time_class")
    }

def parse_lichess(data):
    # Lichess 的 API 回傳的是 NDJSON (Newline Delimited JSON)
    # 你需要將字串切割處理
    return {
        "username": "TargetUser", # Lichess 資料內通常需再對應
        "rating": data.get("players", {}).get("white", {}).get("rating"),
        "date": datetime.fromtimestamp(data.get("createdAt", 0)/1000).strftime('%Y-%m-%d'),
        "result": "win", # 需根據 status 或 winner 欄位判斷
        "mode": data.get("speed")
    }

# 處理 Chess.com 或 Lichess 的轉發邏輯
@app.route('/api/fetch-games', methods=['GET'])
def fetch_games():
    username = request.args.get('username')
    source = request.args.get('source')
    
    try:
        if source == 'chess.com':
            archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
            # 1. 先抓取月份列表
            res = requests.get(archives_url, headers={'User-Agent': 'ChessFetcherApp'}).json()
            # 2. 為了範例，我們只抓最後一個月 (通常是最新)
            latest_month_url = res['archives'][-1]
            games_res = requests.get(latest_month_url, headers={'User-Agent': 'ChessFetcherApp'}).json()
            # 3. 轉換
            formatted_data = [parse_chess_com(g, username) for g in games_res['games']]
            
        elif source == 'lichess':
            url = f"https://lichess.org/api/games/user/{username}?max=10"
            # Lichess 回傳的是 NDJSON，需要按行讀取
            response = requests.get(url, headers={'Accept': 'application/x-ndjson'})
            lines = response.text.strip().split('\n')
            formatted_data = [parse_lichess(json.loads(line)) for line in lines]
            
        else:
            return jsonify({"error": "Invalid source"}), 400
            
        return jsonify(formatted_data)
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)