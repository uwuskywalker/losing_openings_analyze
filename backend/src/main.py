import os
import sys
from pathlib import Path

import psycopg2
from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory import get_platform

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")

def get_db_connection():
    url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(url, sslmode='require')
    return conn

@app.route('/')
def index():
    if (STATIC_DIR / 'index.html').exists():
        return send_from_directory(str(STATIC_DIR), 'index.html')
    return jsonify({"message": "backend is running"})

@app.route('/<path:path>')
def serve_frontend(path):
    full_path = STATIC_DIR / path
    if full_path.is_file():
        return send_from_directory(str(STATIC_DIR), path)
    if (STATIC_DIR / 'index.html').exists():
        return send_from_directory(str(STATIC_DIR), 'index.html')
    return jsonify({"error": "not found"}), 404

@app.route('/api/fetch-games', methods=['GET'])
def fetch_games():
    username = request.args.get('username')
    source = request.args.get('source')
    
    if not username or not source:
        return jsonify({"error": "缺少 username 或 source 參數"}), 400
        
    try:
        # 透過工廠動態取得平台實例
        platform = get_platform(source, username)
        # 核心邏輯永遠不變：不管哪家平台，一律呼叫 fetch_games()
        formatted_data = platform.fetch_games()
        
        return jsonify(formatted_data)
        
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"伺服器錯誤: {e}")
        return jsonify({"error": "內部伺服器錯誤"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    app.run(debug=False, host='0.0.0.0', port=port)