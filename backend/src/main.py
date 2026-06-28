from flask import Flask, request, jsonify
from factory import get_platform

app = Flask(__name__)

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
    app.run(debug=True, host='0.0.0.0',port=5000)