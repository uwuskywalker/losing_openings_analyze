from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# 處理 Chess.com 或 Lichess 的轉發邏輯
@app.route('/api/fetch-games', methods=['GET'])
def fetch_games():
    username = request.args.get('username')
    source = request.args.get('source')

    if source == 'chess.com':
        # Chess.com 的 API 端點
        url = f"https://api.chess.com/pub/player/{username}/games/archives"
    elif source == 'lichess':
        # Lichess 的 API 端點
        url = f"https://lichess.org/api/games/user/{username}?max=10"
    else:
        return jsonify({"error": "Invalid source"}), 400

    try:
        # 使用 requests 呼叫第三方 API
        response = requests.get(url, headers={'Accept': 'application/json'})
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)