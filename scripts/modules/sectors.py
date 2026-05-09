#!/usr/bin/env python3
"""
板块数据获取 - 使用东方财富数据源
"""
import requests
from .config import HEADERS

# 东方财富板块API
EM_CONCEPT_BOARD_URL = "https://push2delay.eastmoney.com/api/qt/clist/get?np=1&fltt=1&invt=2&fs=m:90+t:3+f:!50&fields=f12,f13,f14,f2,f3,f4,f20,f8,f104,f105,f128,f140,f141,f136&fid=f3&pn=1&pz=50&po=1&ut=fa5fd1943c7b386f172d6893dbfba10b"
EM_INDUSTRY_BOARD_URL = "https://push2delay.eastmoney.com/api/qt/clist/get?np=1&fltt=1&invt=2&fs=m:90+t:2&fields=f12,f13,f14,f2,f3,f4,f20,f8,f104,f105,f128,f140,f141,f136&fid=f3&pn=1&pz=50&po=1&ut=fa5fd1943c7b386f172d6893dbfba10b"

def format_market_cap(value):
    """格式化市值"""
    if not value:
        return "-"
    if value >= 1e12:
        return f"{value/1e12:.2f}万亿"
    elif value >= 1e8:
        return f"{value/1e8:.2f}亿"
    else:
        return f"{value/1e4:.2f}万"

def fetch_sectors():
    """
    获取热门板块数据（东方财富数据源）
    返回: [{板块名称, 最新价, 涨跌额, 涨跌幅, 总市值, 换手率, 上涨家数, 下跌家数, 领涨股票}, ...]
    """
    try:
        result = []
        
        # 获取概念板块
        response = requests.get(EM_CONCEPT_BOARD_URL, headers=HEADERS, timeout=15)
        data = response.json()
        
        if data.get("data") and data["data"].get("diff"):
            plate_list = data["data"]["diff"]
            for item in plate_list:
                price = item.get("f2", 0) or 0
                change_pct = item.get("f3", 0) or 0
                change_amt = item.get("f4", 0) or 0
                turnover = item.get("f8", 0) or 0
                market_cap = item.get("f20", 0) or 0
                up_count = item.get("f104", 0) or 0
                down_count = item.get("f105", 0) or 0
                leader_name = item.get("f128", "")
                leader_code = item.get("f140", "")
                leader_is_zt = item.get("f141", 0) == 1
                
                sector = {
                    "板块名称": item.get("f14", ""),
                    "板块代码": item.get("f12", ""),
                    "最新价": price / 100 if price else 0,
                    "涨跌额": change_amt / 100 if change_amt else 0,
                    "涨跌幅": change_pct / 100 if change_pct else 0,
                    "总市值": format_market_cap(market_cap),
                    "总市值_原始": market_cap,
                    "换手率": turnover / 100 if turnover else 0,
                    "上涨家数": up_count,
                    "下跌家数": down_count,
                    "领涨股票": f"{leader_name}({leader_code}){'涨停' if leader_is_zt else ''}",
                    "领涨股名称": leader_name,
                    "领涨股代码": leader_code,
                    "领涨股涨停": leader_is_zt,
                    "type": "concept"
                }
                result.append(sector)
            print(f"[板块] 概念板块: {len(plate_list)} 个")
        
        # 获取行业板块
        response = requests.get(EM_INDUSTRY_BOARD_URL, headers=HEADERS, timeout=15)
        data = response.json()
        
        if data.get("data") and data["data"].get("diff"):
            plate_list = data["data"]["diff"]
            for item in plate_list:
                price = item.get("f2", 0) or 0
                change_pct = item.get("f3", 0) or 0
                change_amt = item.get("f4", 0) or 0
                turnover = item.get("f8", 0) or 0
                market_cap = item.get("f20", 0) or 0
                up_count = item.get("f104", 0) or 0
                down_count = item.get("f105", 0) or 0
                leader_name = item.get("f128", "")
                leader_code = item.get("f140", "")
                leader_is_zt = item.get("f141", 0) == 1
                
                sector = {
                    "板块名称": item.get("f14", ""),
                    "板块代码": item.get("f12", ""),
                    "最新价": price / 100 if price else 0,
                    "涨跌额": change_amt / 100 if change_amt else 0,
                    "涨跌幅": change_pct / 100 if change_pct else 0,
                    "总市值": format_market_cap(market_cap),
                    "总市值_原始": market_cap,
                    "换手率": turnover / 100 if turnover else 0,
                    "上涨家数": up_count,
                    "下跌家数": down_count,
                    "领涨股票": f"{leader_name}({leader_code}){'涨停' if leader_is_zt else ''}",
                    "领涨股名称": leader_name,
                    "领涨股代码": leader_code,
                    "领涨股涨停": leader_is_zt,
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