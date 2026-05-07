"""
获取同花顺热榜 - 大家都在看（1小时）
"""

from .config import session


def fetch_hot_rank():
    """获取同花顺热榜 - 大家都在看（1小时）"""
    try:
        url = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock"
        params = {"stock_type": "a", "type": "hour", "list_type": "normal"}
        resp = session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status_code") == 0 and data.get("data", {}).get("stock_list"):
            stocks = []
            for item in data["data"]["stock_list"]:
                stocks.append({
                    "rank": item["order"],
                    "code": item["code"],
                    "name": item["name"].replace(" ", ""),
                    "price": 0,
                    "change_pct": round(item.get("rise_and_fall", 0), 2),
                    "hot_value": item.get("rate", "0"),
                    "rank_chg": item.get("hot_rank_chg", 0),
                    "popularity_tag": (item.get("tag") or {}).get("popularity_tag", ""),
                    "concept_tags": (item.get("tag") or {}).get("concept_tag", []),
                    "board_info": "",
                    "board_reason": "",
                    "market_cap": "",
                    "turnover": 0,
                    "browse_rank": 0,
                })
            return stocks
        else:
            print(f"热榜API返回异常: {data}")
            return []
    except Exception as e:
        print(f"热榜获取失败: {e}")
        return []
