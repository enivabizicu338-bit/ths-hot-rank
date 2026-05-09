#!/usr/bin/env python3
"""
同花顺热榜数据获取
"""
import requests
from .config import THS_HOT_RANK_URL, HEADERS

def fetch_hot_rank():
    """
    获取同花顺热榜数据
    返回: [{rank, code, name, price, change_pct, hot_value, rank_chg, popularity_tag, concept_tags}, ...]
    """
    try:
        response = requests.get(THS_HOT_RANK_URL, headers=HEADERS, timeout=15)
        data = response.json()
        
        if data.get("status_code") != 0:
            print(f"[同花顺热榜] API返回错误: {data.get('status_msg', '未知错误')}")
            return []
        
        result = []
        stock_list = data.get("data", {}).get("stock_list", [])
        
        for item in stock_list:
            stock = {
                "rank": item.get("rank", 0),
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "price": 0,  # 同花顺热榜API不返回价格，需要从其他接口获取
                "change_pct": item.get("change_pct", 0),
                "hot_value": item.get("hot_value", 0),
                "rank_chg": item.get("rank_chg", 0),
                "popularity_tag": item.get("popularity_tag", ""),
                "concept_tags": item.get("concept_tags", []),
            }
            result.append(stock)
        
        return result
        
    except Exception as e:
        print(f"[同花顺热榜] 获取失败: {e}")
        return []


if __name__ == "__main__":
    import json
    data = fetch_hot_rank()
    print(json.dumps(data[:3], ensure_ascii=False, indent=2))