#!/usr/bin/env python3
"""
同花顺人气数据获取（涨停原因、连板信息等）
"""
import requests
from .config import THS_POPULARITY_URL, HEADERS

def fetch_popularity():
    """
    获取同花顺人气排名数据
    返回: {code: {price, market_cap, board_info, board_reason}, ...}
    """
    result = {}
    
    try:
        # 获取多页数据
        for page in range(1, 6):  # 获取前5页
            params = {
                "page": page,
                "perpage": 20,
                "type": "stock",
                "pool": "hs"
            }
            
            response = requests.get(THS_POPULARITY_URL, params=params, headers=HEADERS, timeout=15)
            data = response.json()
            
            if data.get("errorCode") != 0:
                continue
            
            items = data.get("data", {}).get("list", [])
            if not items:
                break
            
            for item in items:
                code = item.get("code", "")
                if code:
                    result[code] = {
                        "price": item.get("price", 0),
                        "market_cap": item.get("market_cap", 0),
                        "board_info": item.get("board_info", ""),  # 连板信息
                        "board_reason": item.get("board_reason", ""),  # 涨停原因
                    }
        
        return result
        
    except Exception as e:
        print(f"[同花顺人气] 获取失败: {e}")
        return {}


if __name__ == "__main__":
    import json
    data = fetch_popularity()
    print(f"获取到 {len(data)} 只股票")
    # 打印前3条
    for code in list(data.keys())[:3]:
        print(f"{code}: {json.dumps(data[code], ensure_ascii=False)}")