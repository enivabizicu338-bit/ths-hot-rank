#!/usr/bin/env python3
"""
本地Web服务 - 同花顺热榜数据展示
运行: python app.py
访问: http://localhost:5000
"""
import json
import os
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
GITHUB_RAW_URL = "https://raw.githubusercontent.com/enivabizicu338-bit/ths-hot-rank/main/data"

_news_cache = {"data": [], "update_time": 0}
_keywords_cache = {"data": [], "update_time": 0}
_CACHE_TTL = 20 * 60  # 20分钟

def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载 {filename} 失败: {e}")
        return None

def fetch_from_github(filename):
    import requests
    try:
        url = f"{GITHUB_RAW_URL}/{filename}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
    except Exception as e:
        print(f"从GitHub拉取 {filename} 失败: {e}")
    return None

def fetch_news_from_api():
    import requests as _req
    import re as _re
    url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
    params = {"client":"web","biz":"web_news_col","column":"353","order":"1","needInteractData":"0","page_index":"1","page_size":"30","fields":"code,showTime,title,mediaName,summary,image,url,uniqueUrl,Np_dst","types":"1,20","req_trace":str(int(time.time()*1000))}
    headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Referer":"https://finance.eastmoney.com/"}
    r = _req.get(url, params=params, headers=headers, timeout=15)
    text = _re.sub(r'^jQuery\d+_\d+\(', '', r.text)
    text = _re.sub(r'\)$', '', text)
    data = json.loads(text)
    news_list = data.get("data", {}).get("list", [])
    return [{"title":n.get("title",""),"summary":n.get("summary",""),"showTime":n.get("showTime",""),"mediaName":n.get("mediaName",""),"url":n.get("url",""),"image":n.get("image","")} for n in news_list]

def extract_keywords_from_news(news_list):
    try:
        from scripts.modules.keywords import extract_keywords
        return extract_keywords(news_list)
    except Exception as e:
        print(f"关键词提取失败: {e}")
        return []

def refresh_news_cache():
    global _news_cache, _keywords_cache
    try:
        news = fetch_news_from_api()
        if news:
            _news_cache = {"data": news, "update_time": time.time()}
            keywords = extract_keywords_from_news(news)
            _keywords_cache = {"data": keywords, "update_time": time.time()}
            print(f"[缓存] 新闻{len(news)}条, 关键词{len(keywords)}个")
    except Exception as e:
        print(f"[缓存] 刷新失败: {e}")

def background_refresh():
    while True:
        time.sleep(_CACHE_TTL)
        refresh_news_cache()

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/current')
def api_current():
    data = load_json('current.json')
    if not data: data = fetch_from_github('current.json')
    return jsonify(data or {})

@app.route('/api/skyrocket')
def api_skyrocket():
    data = load_json('skyrocket.json')
    if not data: data = fetch_from_github('skyrocket.json')
    return jsonify(data or {})

@app.route('/api/sectors')
def api_sectors():
    data = load_json('sectors.json')
    if not data: data = fetch_from_github('sectors.json')
    return jsonify(data or {})

@app.route('/api/board_strength')
def api_board_strength():
    data = load_json('board_strength.json')
    if not data: data = fetch_from_github('board_strength.json')
    return jsonify(data or {})

@app.route('/api/snapshots')
def api_snapshots():
    data = load_json('snapshots.json')
    if not data: data = fetch_from_github('snapshots.json')
    return jsonify(data or [])

@app.route('/api/rank_history')
def api_rank_history():
    """获取排名历史走势数据"""
    try:
        from scripts.modules.rank_history import get_top_stocks_rank_history
        result = get_top_stocks_rank_history(top_n=30)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "time_labels": [], "stocks": []})

@app.route('/api/news')
def api_news():
    now = time.time()
    if now - _news_cache["update_time"] > _CACHE_TTL:
        refresh_news_cache()
    return jsonify({"update_time": datetime.fromtimestamp(_news_cache["update_time"]).strftime("%Y-%m-%d %H:%M:%S") if _news_cache["update_time"] else "", "data": _news_cache["data"]})

@app.route('/api/keywords')
def api_keywords():
    now = time.time()
    if now - _keywords_cache["update_time"] > _CACHE_TTL:
        refresh_news_cache()
    return jsonify({"update_time": datetime.fromtimestamp(_keywords_cache["update_time"]).strftime("%Y-%m-%d %H:%M:%S") if _keywords_cache["update_time"] else "", "data": _keywords_cache["data"]})

@app.route('/api/sync')
def api_sync():
    files = ['current.json', 'skyrocket.json', 'sectors.json', 'board_strength.json', 'snapshots.json']
    results = {}
    for f in files:
        results[f] = 'success' if fetch_from_github(f) else 'failed'
    return jsonify({'status': 'ok', 'results': results})

@app.route('/api/fetch')
def api_fetch():
    import subprocess
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'fetch_data.py')
        result = subprocess.run(['python', script_path], capture_output=True, text=True, timeout=60)
        return jsonify({'status': 'ok' if result.returncode == 0 else 'error', 'output': result.stdout, 'error': result.stderr})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/api/recommend')
def api_recommend():
    """生成新推荐"""
    try:
        from scripts.modules.recommender import generate_recommendations
        result = generate_recommendations()
        return jsonify(result or {"error": "no data"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/recommend/history')
def api_recommend_history():
    """获取历史推荐记录"""
    try:
        from scripts.modules.recommender import load_history
        history = load_history()
        return jsonify(history)
    except Exception as e:
        return jsonify([])

@app.route('/api/recommend/backtest/<int:index>')
def api_recommend_backtest(index):
    """回测第index条推荐(0=最新)"""
    try:
        from scripts.modules.recommender import load_history, backtest_recommendation
        history = load_history()
        if index < 0 or index >= len(history):
            return jsonify({"error": "index out of range"})
        current_data = load_json('current.json')
        result = backtest_recommendation(history[index], current_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/strategies')
def api_strategies():
    """获取策略配置和统计数据"""
    try:
        from scripts.modules.strategy_engine import get_strategy_summary
        return jsonify(get_strategy_summary())
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/attribution/history')
def api_attribution_history():
    """获取归因分析历史"""
    try:
        from scripts.modules.attribution import load_attributions
        return jsonify(load_attributions())
    except Exception as e:
        return jsonify([])

@app.route('/api/attribution/backtest/<int:index>')
def api_attribution_backtest(index):
    """对第index条推荐进行事后归因分析"""
    try:
        from scripts.modules.recommender import load_history
        from scripts.modules.attribution import batch_post_attribution, save_attribution

        history = load_history()
        if index < 0 or index >= len(history):
            return jsonify({"error": "index out of range"})

        current_data = load_json('current.json')
        result = batch_post_attribution(history[index], current_data)

        if result:
            save_attribution(result)

        return jsonify(result or {"error": "backtest failed"})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs('static', exist_ok=True)
    print("正在从GitHub拉取最新数据...")
    for f in ['current.json', 'skyrocket.json', 'sectors.json', 'board_strength.json', 'snapshots.json']:
        fetch_from_github(f)
    print("数据拉取完成!")
    print("正在获取新闻和关键词...")
    refresh_news_cache()
    t = threading.Thread(target=background_refresh, daemon=True)
    t.start()
    print("后台新闻刷新已启动（每20分钟）")
    print("\n启动Web服务: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)