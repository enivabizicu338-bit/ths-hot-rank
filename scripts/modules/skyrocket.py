#!/usr/bin/env python3
"""
同花顺飙升榜数据获取
"""
import requests
from .config import THS_SKYROCKET_URL, HEADERS

def fetch_skyrocket():
    """
    获取同花顺飙升榜数据
    返回: [{rank, code, name, rate, rise_and_fall, hot_rank_chg, concept_tags, popularity_tag}, ...]
    """
    try:
        response = requests.get(THS_SKYROCKET_URL, headers=HEADERS, timeout=15)
        data = response.json()

        if data.get("status_code") != 0:
            print(f"[飙升榜] API返回错误: {data.get('status_msg', '未知错误')}")
            return []

        result = []
        stock_list = data.get("data", {}).get("stock_list", [])

        for item in stock_list:
            tag = item.get("tag", {}) or {}
            rise = item.get("rise_and_fall")
            stock = {
                "rank": item.get("order", 0),
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "rate": item.get("rate", "0"),  # 飙升速率
                "change_pct": round(rise, 2) if rise is not None else 0,
                "hot_rank_chg": item.get("hot_rank_chg", 0),
                "popularity_tag": tag.get("popularity_tag", ""),
                "concept_tags": tag.get("concept_tag", []),
                "analyse": item.get("analyse", ""),
            }
            result.append(stock)

        print(f"[飙升榜] 获取 {len(result)} 只股票")
        return result

    except Exception as e:
        print(f"[飙升榜] 获取失败: {e}")
        return []