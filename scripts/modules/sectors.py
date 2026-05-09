#!/usr/bin/env python3
"""
板块数据获取
"""
import requests
from .config import HEADERS

def fetch_sectors():
    """
    获取热门板块数据
    返回: [{板块名称, 涨跌幅, 热度, 上板家数}, ...]
    """
    try:
        # 同花顺板块API
        url = "https://dq.10jqka.com.cn/fuyao/hotlist/v2/hotlist/v2/all/plate"
        
        response = requests.get(url, headers=HEADERS, timeout=15)
        data = response.json()
        
        if data.get("status_code") != 0:
            print(f"[板块] API返回错误: {data.get('status_msg', '未知错误')}")
            return []
        
        result = []
        plate_list = data.get("data", {}).get("plate_list", [])
        
        for item in plate_list:
            sector = {
                "板块名称": item.get("name", ""),
                "涨跌幅": item.get("change_pct", 0),
                "热度": item.get("hot_value", 0),
                "上板家数": item.get("board_num", ""),
            }
            result.append(sector)
        
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