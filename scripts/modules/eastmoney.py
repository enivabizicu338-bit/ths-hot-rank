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

    result = {code: {"turnover": 0, "browse_rank": 0, "price": 0, "change_pct": 0} for code in codes}

    # 1. 批量获取今日浏览排名 + 换手率（东财选股器API，获取前200名）
    try:
        url = "https://data.eastmoney.com/dataapi/xuangu/list"
        all_items = []
        # 获取前200名，每页100条，需要2页
        for page in range(1, 3):
            params = {
                "st": "BROWSE_RANK",
                "sr": "1",
                "ps": "100",
                "p": str(page),
                "sty": "SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,NEW_PRICE,CHANGE_RATE,TURNOVERRATE,BROWSE_RANK",
                "filter": "(BROWSE_RANK>0)(BROWSE_RANK<=200)",
                "source": "SELECT_SECURITIES",
                "client": "WEB",
                "hyversion": "v2",
            }
            resp = em_session.get(url, params=params, timeout=15)
            data = resp.json()
            items = data.get("result", {}).get("data", [])
            all_items.extend(items)
            if len(items) < 100:
                break
        items = all_items
        # 建立代码 -> {browse_rank, turnover, price, change_pct} 映射
        browse_map = {}
        for item in items:
            code = item.get("SECURITY_CODE", "")
            browse_rank = item.get("BROWSE_RANK", 0)
            turnover = item.get("TURNOVERRATE", 0)
            price = item.get("NEW_PRICE", 0)
            change_pct = item.get("CHANGE_RATE", 0)
            browse_map[code] = {
                "browse_rank": browse_rank,
                "turnover": round(float(turnover), 2) if turnover else 0,
                "price": round(float(price), 2) if price else 0,
                "change_pct": round(float(change_pct), 2) if change_pct else 0,
            }
        # 匹配热榜股票
        browse_count = 0
        turnover_count = 0
        price_count = 0
        for code in codes:
            if code in browse_map:
                result[code]["browse_rank"] = browse_map[code]["browse_rank"]
                result[code]["turnover"] = browse_map[code]["turnover"]
                result[code]["price"] = browse_map[code]["price"]
                result[code]["change_pct"] = browse_map[code]["change_pct"]
                browse_count += 1
                if browse_map[code]["turnover"] > 0:
                    turnover_count += 1
                if browse_map[code]["price"] > 0:
                    price_count += 1
        print(f"东财浏览排名: 匹配 {browse_count}/{len(codes)} 只, 换手率 {turnover_count} 只, 实时价格 {price_count} 只")
    except Exception as e:
        print(f"东财浏览排名API失败: {e}")

    # 2. 补充实时价格+涨跌幅+换手率（并发单股接口，覆盖全部股票确保价格正确）
    # 注意：即使批量API返回了价格，也要用单股接口验证（更可靠）
    missing_codes = [c for c in codes if result[c]["price"] == 0]
    if missing_codes:
        def fetch_one_stock(code):
            try:
                market = "1" if code.startswith("6") else "0"
                url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={market}.{code}&fields=f43,f170,f168&fltt=2"
                resp = em_session.get(url, timeout=8)
                d = resp.json().get("data", {})
                price = float(d.get("f43", 0)) if d.get("f43") else 0
                change_pct = float(d.get("f170", 0)) if d.get("f170") else 0
                turnover = float(d.get("f168", 0)) if d.get("f168") else 0
                return code, round(price, 2), round(change_pct, 2), round(turnover, 2)
            except Exception as e:
                print(f"  单股查询失败 {code}: {e}")
                return code, 0, 0, 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_one_stock, code): code for code in missing_codes}
            for future in as_completed(futures):
                code, price, change_pct, turnover = future.result()
                if price > 0:
                    result[code]["price"] = price
                if change_pct != 0:
                    result[code]["change_pct"] = change_pct
                if turnover > 0:
                    result[code]["turnover"] = turnover

        extra_price = sum(1 for c in missing_codes if result[c]["price"] > 0)
        extra_turnover = sum(1 for c in missing_codes if result[c]["turnover"] > 0)
        total_price = sum(1 for c in codes if result[c]["price"] > 0)
        total_turnover = sum(1 for c in codes if result[c]["turnover"] > 0)
        print(f"东财补充: 实时价格 {extra_price} 只(总计 {total_price}/{len(codes)}), 换手率 {extra_turnover} 只(总计 {total_turnover}/{len(codes)})")

    # 3. 批量获取换手率（clist/get API，f8=换手率，覆盖全部股票）
    missing_turnover = [c for c in codes if result[c]["turnover"] == 0]
    if missing_turnover:
        try:
            # 构建secids参数：市场.代码，用逗号分隔
            secids = []
            for code in missing_turnover:
                market = "1" if code.startswith("6") else "0"
                secids.append(f"{market}.{code}")
            # 分批请求（每批500个）
            batch_size = 500
            for i in range(0, len(secids), batch_size):
                batch_secids = ",".join(secids[i:i+batch_size])
                url = "https://push2.eastmoney.com/api/qt/clist/get"
                params = {
                    "pn": 1, "pz": batch_size, "po": 1, "np": 1,
                    "fltt": 2, "invt": 2,
                    "fid": "f8",
                    "fs": f"b:{batch_secids}",
                    "fields": "f12,f8",
                }
                resp = em_session.get(url, params=params, timeout=15)
                items = resp.json().get("data", {}).get("diff", [])
                for item in items:
                    code = item.get("f12", "")
                    turnover = float(item.get("f8", 0)) if item.get("f8") else 0
                    if code in result and turnover > 0:
                        result[code]["turnover"] = round(turnover, 2)
            final_turnover = sum(1 for c in codes if result[c]["turnover"] > 0)
            print(f"东财换手率批量: 补充 {len(missing_turnover)} 只, 最终覆盖 {final_turnover}/{len(codes)} 只")
        except Exception as e:
            print(f"东财换手率批量API失败: {e}")

    return result
