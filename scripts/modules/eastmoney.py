"""
获取东方财富数据 - 今日浏览排名 + 换手率（一个API同时获取）
"""

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


def fetch_eastmoney_data(codes):
    """获取东方财富数据 - 今日浏览排名 + 换手率（一个API同时获取）"""
    em_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://data.eastmoney.com/xuangu/",
    }
    em_session = requests.Session()
    em_session.headers.update(em_headers)

    result = {code: {"turnover": 0, "browse_rank": 0} for code in codes}

    # 1. 批量获取今日浏览排名 + 换手率（东财选股器API，一次请求搞定）
    try:
        url = "https://data.eastmoney.com/dataapi/xuangu/list"
        params = {
            "st": "BROWSE_RANK",
            "sr": "1",
            "ps": "100",
            "p": "1",
            "sty": "SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,NEW_PRICE,CHANGE_RATE,TURNOVERRATE,BROWSE_RANK",
            "filter": "(BROWSE_RANK>0)(BROWSE_RANK<=200)",
            "source": "SELECT_SECURITIES",
            "client": "WEB",
            "hyversion": "v2",
        }
        resp = em_session.get(url, params=params, timeout=15)
        data = resp.json()
        items = data.get("result", {}).get("data", [])
        # 建立代码 -> {browse_rank, turnover} 映射
        browse_map = {}
        for item in items:
            code = item.get("SECURITY_CODE", "")
            browse_rank = item.get("BROWSE_RANK", 0)
            turnover = item.get("TURNOVERRATE", 0)
            browse_map[code] = {"browse_rank": browse_rank, "turnover": round(float(turnover), 2) if turnover else 0}
        # 匹配热榜股票
        browse_count = 0
        turnover_count = 0
        for code in codes:
            if code in browse_map:
                result[code]["browse_rank"] = browse_map[code]["browse_rank"]
                result[code]["turnover"] = browse_map[code]["turnover"]
                browse_count += 1
                if browse_map[code]["turnover"] > 0:
                    turnover_count += 1
        print(f"东财浏览排名: 匹配 {browse_count}/{len(codes)} 只, 换手率 {turnover_count} 只")
    except Exception as e:
        print(f"东财浏览排名API失败: {e}")

    # 2. 补充换手率（并发单股接口，覆盖浏览排名API未覆盖的股票）
    missing_codes = [c for c in codes if result[c]["turnover"] == 0]
    if missing_codes:
        def fetch_one_turnover(code):
            try:
                market = "1" if code.startswith("6") else "0"
                url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={market}.{code}&fields=f168&fltt=2"
                resp = em_session.get(url, timeout=8)
                d = resp.json().get("data", {})
                raw = d.get("f168", 0)
                turnover = float(raw) if raw else 0
                return code, round(turnover, 2)
            except Exception:
                return code, 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_one_turnover, code): code for code in missing_codes}
            for future in as_completed(futures):
                code, turnover = future.result()
                if turnover > 0:
                    result[code]["turnover"] = turnover

        extra_count = sum(1 for c in missing_codes if result[c]["turnover"] > 0)
        total_turnover = sum(1 for c in codes if result[c]["turnover"] > 0)
        print(f"东财换手率(补充): {extra_count} 只, 总计 {total_turnover}/{len(codes)} 只")

    return result
