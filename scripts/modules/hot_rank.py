#!/usr/bin/env python3
"""
同花顺热榜数据获取
"""
import requests
from .config import THS_HOT_RANK_URL, HEADERS

# 腾讯股票API
TENCENT_STOCK_API = "https://qt.gtimg.cn/q="

def fetch_stock_prices(codes):
    """
    通过腾讯API获取股票现价和换手率
    codes: 股票代码列表，如 ['600522', '002281']
    返回: {code: {"price": float, "turnover": float}, ...}
    腾讯API字段索引: 3=现价, 38=换手率(%)
    """
    if not codes:
        return {}
    
    # 转换股票代码格式：沪市用sh，深市用sz
    stock_list = []
    for code in codes:
        if code.startswith('6'):
            stock_list.append(f'sh{code}')
        elif code.startswith('0') or code.startswith('3'):
            stock_list.append(f'sz{code}')
        elif code.startswith('68'):  # 科创板
            stock_list.append(f'sh{code}')
        else:
            stock_list.append(f'sz{code}')
    
    try:
        url = TENCENT_STOCK_API + ','.join(stock_list)
        response = requests.get(url, timeout=10)
        text = response.text
        
        result = {}
        lines = text.strip().split('\n')
        for i, line in enumerate(lines):
            if not line or '~' not in line:
                continue
            # 解析格式：v_sh600522="1~中天科技~600522~40.90~...~3.67~..."
            parts = line.split('~')
            if len(parts) >= 39:
                code = parts[2]
                try:
                    price = float(parts[3])
                    turnover = float(parts[38])
                    result[code] = {"price": price, "turnover": turnover}
                except (ValueError, IndexError):
                    result[code] = {"price": 0, "turnover": 0}
        
        return result
        
    except Exception as e:
        print(f"[腾讯API] 获取现价/换手率失败: {e}")
        return {}

def fetch_hot_rank():
    """
    获取同花顺热榜数据
    返回: [{rank, code, name, price, change_pct, hot_value, rank_chg, popularity_tag, concept_tags, analyse, turnover}, ...]
    """
    try:
        response = requests.get(THS_HOT_RANK_URL, headers=HEADERS, timeout=15)
        data = response.json()

        if data.get("status_code") != 0:
            print(f"[同花顺热榜] API返回错误: {data.get('status_msg', '未知错误')}")
            return []

        result = []
        stock_list = data.get("data", {}).get("stock_list", [])
        
        # 收集所有股票代码
        codes = [item.get("code", "") for item in stock_list]
        
        # 批量获取现价和换手率
        print(f"[腾讯API] 正在获取 {len(codes)} 只股票的现价和换手率...")
        price_map = fetch_stock_prices(codes)
        print(f"[腾讯API] 成功获取 {len(price_map)} 只股票数据")

        for item in stock_list:
            tag = item.get("tag", {}) or {}
            code = item.get("code", "")
            stock_info = price_map.get(code, {"price": 0, "turnover": 0})
            stock = {
                "rank": item.get("order", 0),
                "code": code,
                "name": item.get("name", ""),
                "price": stock_info["price"],
                "turnover": round(stock_info["turnover"], 2),
                "change_pct": round(item.get("rise_and_fall", 0), 2),
                "hot_value": item.get("rate", "0"),
                "rank_chg": item.get("hot_rank_chg", 0),
                "popularity_tag": tag.get("popularity_tag", ""),
                "concept_tags": tag.get("concept_tag", []),
                "analyse": item.get("analyse", ""),
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