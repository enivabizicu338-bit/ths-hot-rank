#!/usr/bin/env python3
"""
本地Web服务 - 同花顺热榜数据展示
运行: python app.py
访问: http://localhost:5000
"""
import json
import os
from datetime import datetime
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# GitHub原始数据URL
GITHUB_RAW_URL = "https://raw.githubusercontent.com/enivabizicu338-bit/ths-hot-rank/main/data"

def load_json(filename):
    """加载JSON数据"""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载 {filename} 失败: {e}")
        return None

def fetch_from_github(filename):
    """从GitHub拉取数据"""
    import requests
    try:
        url = f"{GITHUB_RAW_URL}/{filename}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # 保存到本地
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
    except Exception as e:
        print(f"从GitHub拉取 {filename} 失败: {e}")
    return None

@app.route('/')
def index():
    """主页 - 返回静态HTML"""
    return send_from_directory('static', 'index.html')

@app.route('/api/current')
def api_current():
    """获取当前热榜数据"""
    data = load_json('current.json')
    if not data:
        data = fetch_from_github('current.json')
    return jsonify(data or {})

@app.route('/api/skyrocket')
def api_skyrocket():
    """获取飙升榜数据"""
    data = load_json('skyrocket.json')
    if not data:
        data = fetch_from_github('skyrocket.json')
    return jsonify(data or {})

@app.route('/api/sectors')
def api_sectors():
    """获取板块数据"""
    data = load_json('sectors.json')
    if not data:
        data = fetch_from_github('sectors.json')
    return jsonify(data or {})

@app.route('/api/board_strength')
def api_board_strength():
    """获取板块梯队强度"""
    data = load_json('board_strength.json')
    if not data:
        data = fetch_from_github('board_strength.json')
    return jsonify(data or {})

@app.route('/api/snapshots')
def api_snapshots():
    """获取历史快照"""
    data = load_json('snapshots.json')
    if not data:
        data = fetch_from_github('snapshots.json')
    return jsonify(data or [])


@app.route('/api/news')
def api_news():
    """获取最新A股新闻（实时从东方财富API获取）"""
    try:
        import requests as _req
        import re as _re
        import time as _time
        import json as _json
        url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
        params = {"client":"web","biz":"web_news_col","column":"353","order":"1","needInteractData":"0","page_index":"1","page_size":"30","fields":"code,showTime,title,mediaName,summary,image,url,uniqueUrl,Np_dst","types":"1,20","req_trace":str(int(_time.time()*1000))}
        headers = {"User-Agent":"Mozilla/5.0","Referer":"https://finance.eastmoney.com/"}
        r = _req.get(url, params=params, headers=headers, timeout=15)
        text = _re.sub(r'^jQuery\d+_\d+\(', '', r.text)
        text = _re.sub(r'\)$', '', text)
        data = _json.loads(text)
        news_list = data.get("data", {}).get("list", [])
        result = [{"title":n.get("title",""),"summary":n.get("summary",""),"showTime":n.get("showTime",""),"mediaName":n.get("mediaName",""),"url":n.get("url",""),"image":n.get("image","")} for n in news_list]
        return jsonify({"update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "data": result})
    except Exception as e:
        return jsonify({"data": [], "error": str(e)})@app.route('/api/sync')
def api_sync():
    """从GitHub同步所有数据"""
    files = ['current.json', 'skyrocket.json', 'sectors.json', 'board_strength.json', 'snapshots.json']
    results = {}
    for f in files:
        results[f] = 'success' if fetch_from_github(f) else 'failed'
    return jsonify({'status': 'ok', 'results': results})

@app.route('/api/fetch')
def api_fetch():
    """手动触发数据采集"""
    import subprocess
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'fetch_data.py')
        result = subprocess.run(['python', script_path], capture_output=True, text=True, timeout=60)
        return jsonify({
            'status': 'ok' if result.returncode == 0 else 'error',
            'output': result.stdout,
            'error': result.stderr
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    # 确保目录存在
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # 启动时从GitHub拉取数据
    print("正在从GitHub拉取最新数据...")
    fetch_from_github('current.json')
    fetch_from_github('skyrocket.json')
    fetch_from_github('sectors.json')
    fetch_from_github('board_strength.json')
    fetch_from_github('snapshots.json')
    print("数据拉取完成!")
    
    print("\n启动Web服务: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)