#!/usr/bin/env python3
"""
雪球热榜数据获取
"""
import requests
import json
from .config import DATA_DIR

def fetch_xueqiu_hot():
    """
    获取雪球热股排名
    返回: {code: rank, ...}
    """
    result = {}
    
    try:
        # 雪球热榜API
        url = "https://stock.xueqiu.com/v5/stock/hot_stock/list.json"
        params = {
            "size": 100,
            "type": 10,
            "_": int(__import__('time').time() * 1000)
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://xueqiu.com/",
        }
        
        # 先访问首页获取cookie
        session = requests.Session()
        session.get("https://xueqiu.com", headers=headers, timeout=10)
        
        response = session.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if data.get("error_code") == 0:
            items = data.get("data", {}).get("items", [])
            for idx, item in enumerate(items):
                code = item.get("code", "")
                if code:
                    result[code] = idx + 1
        
        return result
        
    except Exception as e:
        print(f"[雪球] 获取失败: {e}")
        return {}


def save_xueqiu_data(xueqiu_rank):
    """
    保存雪球数据为JSON格式
    """
    try:
        # 转换为列表格式
        data = []
        for code, rank in sorted(xueqiu_rank.items(), key=lambda x: x[1]):
            data.append({
                "code": code,
                "rank": rank
            })
        
        xueqiu_file = DATA_DIR / "xueqiu_hot.json"
        with open(xueqiu_file, "w", encoding="utf-8") as fp:
            json.dump({
                "update_time": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data": data
            }, fp, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"[雪球] 保存失败: {e}")
        return False


if __name__ == "__main__":
    data = fetch_xueqiu_hot()
    print(f"获取到 {len(data)} 只股票")
    # 打印前5条
    for code in list(data.keys())[:5]:
        print(f"{code}: #{data[code]}")