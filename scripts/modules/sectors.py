#!/usr/bin/env python3
"""
板块数据获取
"""
import requests
from .config import HEADERS, THS_PLATE_CONCEPT_URL, THS_PLATE_INDUSTRY_URL

def fetch_sectors():
    """
    获取热门板块数据
    返回: [{板块名称, 涨跌幅, 热度, 上板家数}, ...]
    """
    try:
        result = []
        
        # 获取概念板块
        response = requests.get(THS_PLATE_CONCEPT_URL, headers=HEADERS, timeout=15)
        data = response.json()
        
        if data.get("status_code") == 0:
            plate_list = data.get("data", {}).get("plate_list", [])
            for item in plate_list:
                # 解析上板家数 (如 "15家涨停" -> 15)
                tag = item.get("tag", "")
                board_num = 0
                if tag:
                    import re
                    match = re.search(r'(\d+)', tag)
                    if match:
                        board_num = int(match.group(1))
                
                sector = {
                    "板块名称": item.get("name", ""),
                    "涨跌幅": round(item.get("rise_and_fall", 0), 2),
                    "热度": item.get("rate", "0"),
                    "上板家数": f"{board_num}家",
                    "board_num": board_num,
                    "type": "concept"
                }
                result.append(sector)
            print(f"[板块] 概念板块: {len(plate_list)} 个")
        
        # 获取行业板块
        response = requests.get(THS_PLATE_INDUSTRY_URL, headers=HEADERS, timeout=15)
        data = response.json()
        
        if data.get("status_code") == 0:
            plate_list = data.get("data", {}).get("plate_list", [])
            for item in plate_list:
                tag = item.get("tag", "")
                board_num = 0
                if tag:
                    import re
                    match = re.search(r'(\d+)', tag)
                    if match:
                        board_num = int(match.group(1))
                
                sector = {
                    "板块名称": item.get("name", ""),
                    "涨跌幅": round(item.get("rise_and_fall", 0), 2),
                    "热度": item.get("rate", "0"),
                    "上板家数": f"{board_num}家",
                    "board_num": board_num,
                    "type": "industry"
                }
                result.append(sector)
            print(f"[板块] 行业板块: {len(plate_list)} 个")
        
        return result
        
    except Exception as e:
        print(f"[板块] 获取失败: {e}")
        return []


def dedup_sectors(sectors):
    """
    板块去重合并
    """
    seen = set()
    result = []
    for s in sectors:
        name = s.get("板块名称", "")
        if name and name not in seen:
            seen.add(name)
            result.append(s)
    return result


if __name__ == "__main__":
    import json
    data = fetch_sectors()
    print(f"获取到 {len(data)} 个板块")
    print(json.dumps(data[:3], ensure_ascii=False, indent=2))