"""
获取同花顺人气排名 - 包含几天几板、涨停原因、现价、流通市值
"""

from .config import session


def fetch_popularity():
    """获取同花顺人气排名 - 包含几天几板、涨停原因、现价、流通市值"""
    try:
        url = "https://basic.10jqka.com.cn/api/stockph/popularity/top/"
        headers = {
            "Referer": "https://basic.10jqka.com.cn/basicph/popularityRanking.html",
        }
        resp = session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status_code") == 0 and data.get("data", {}).get("list"):
            pop_map = {}
            for item in data["data"]["list"]:
                code = item.get("code", "")
                # 几天几板
                change_days = item.get("change_days", "")
                change_section = item.get("change_section", "")
                if change_days and change_section:
                    board_info = f"{change_days}天{change_section}板"
                elif change_days:
                    board_info = f"{change_days}天"
                else:
                    board_info = ""
                # 涨停原因
                board_reason = item.get("change_reason", "")
                # 现价
                price = item.get("price", "0")
                # 流通市值（转换为亿）
                cap_raw = item.get("circulate_market_value", "0")
                try:
                    cap_val = float(cap_raw) / 1e8
                    market_cap = f"{cap_val:.1f}亿"
                except (ValueError, TypeError):
                    market_cap = ""
                pop_map[code] = {
                    "board_info": board_info,
                    "board_reason": board_reason,
                    "price": price,
                    "market_cap": market_cap,
                }
            print(f"人气排名: {len(pop_map)} 条")
            return pop_map
        else:
            print(f"人气排名API返回异常: {data}")
            return {}
    except Exception as e:
        print(f"人气排名获取失败: {e}")
        return {}
