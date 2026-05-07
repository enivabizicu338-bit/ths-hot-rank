#!/usr/bin/env python3
"""
采集同花顺热榜数据并保存为 JSON
数据来源: 同花顺官方API (dq.10jqka.com.cn + basic.10jqka.com.cn)
供 GitHub Actions 定时任务使用
"""

import json
import requests
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; Pixel 3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
    "Referer": "https://eq.10jqka.com.cn/frontend/thsTopRank/index.html",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)


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


def fetch_sectors():
    """获取同花顺热门概念板块"""
    try:
        url = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/plate"
        params = {"type": "concept"}
        resp = session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status_code") == 0 and data.get("data", {}).get("plate_list"):
            sectors = []
            for item in data["data"]["plate_list"]:
                sectors.append({
                    "板块名称": item.get("name", ""),
                    "涨跌幅": round(item.get("rise_and_fall", 0), 2),
                    "热度": item.get("rate", "0"),
                    "热度标签": item.get("hot_tag", ""),
                    "标签": item.get("tag", ""),
                    "上板家数": item.get("tag", ""),
                    "领涨股票": "",
                })
            return sectors
        else:
            print(f"板块API返回异常: {data}")
            return []
    except Exception as e:
        print(f"板块获取失败: {e}")
        return []


def fetch_sector_leaders(ths_sector_names):
    """获取热门概念板块的龙头股（前3只涨幅最大）- 独立模块，不影响主流程
    ths_sector_names: 同花顺板块名称列表，用于匹配东方财富板块
    """
    print("开始获取板块龙头股...")
    try:
        em_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://data.eastmoney.com/",
        }
        em_session = requests.Session()
        em_session.headers.update(em_headers)
        url = "https://push2.eastmoney.com/api/qt/clist/get"

        # 1. 获取东方财富全部概念板块列表，建立 名称->代码 映射
        params = {
            "pn": 1, "pz": 500, "po": 1, "np": 1,
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "fltt": 2, "invt": 2, "fid": "f3",
            "fs": "m:90+t:3",
            "fields": "f12,f14,f3",
        }
        resp = em_session.get(url, params=params, timeout=15)
        em_sectors = resp.json().get("data", {}).get("diff", [])
        if not em_sectors:
            print("板块龙头股: 东方财富板块列表为空")
            return {}

        # 建立 东方财富板块名称 -> 板块代码 的映射
        em_name_map = {}
        for sec in em_sectors:
            em_name_map[sec.get("f14", "")] = sec.get("f12", "")

        # 2. 对每个同花顺板块名称，模糊匹配东方财富板块
        def find_em_code(ths_name):
            """模糊匹配同花顺板块名到东方财富板块代码"""
            # 精确匹配
            if ths_name in em_name_map:
                return ths_name, em_name_map[ths_name]
            # 去掉后缀匹配: "XX概念" -> "XX", "XX(YY)" -> "XX"
            base = ths_name.replace("概念", "").replace("（", "(").replace("）", ")")
            paren_idx = base.find("(")
            if paren_idx > 0:
                base = base[:paren_idx].strip()
            if base in em_name_map:
                return base, em_name_map[base]
            # 反向: 东方财富名称包含同花顺基础名
            for em_name, em_code in em_name_map.items():
                em_base = em_name.replace("概念", "")
                if base in em_base or em_base in base:
                    return em_name, em_code
            return None, None

        # 3. 对匹配到的板块获取涨幅前3的龙头股
        leaders_map = {}
        matched = 0
        for ths_name in ths_sector_names:
            em_name, em_code = find_em_code(ths_name)
            if not em_code:
                leaders_map[ths_name] = []
                continue
            matched += 1
            try:
                params2 = {
                    "pn": 1, "pz": 3, "po": 1, "np": 1,
                    "ut": "b2884a393a59ad64002292a3e90d46a5",
                    "fltt": 2, "invt": 2, "fid": "f3",
                    "fs": f"b:{em_code}+f:!50",
                    "fields": "f12,f14,f2,f3",
                }
                resp2 = em_session.get(url, params=params2, timeout=10)
                stocks = resp2.json().get("data", {}).get("diff", [])
                leaders = []
                for s in stocks:
                    leaders.append({
                        "code": s.get("f12", ""),
                        "name": s.get("f14", ""),
                        "price": s.get("f2", 0),
                        "change_pct": s.get("f3", 0),
                    })
                leaders_map[ths_name] = leaders
            except Exception:
                leaders_map[ths_name] = []

        print(f"板块龙头股: 匹配 {matched}/{len(ths_sector_names)} 个板块")
        return leaders_map
    except Exception as e:
        print(f"板块龙头股获取失败: {e}")
        return {}


def load_snapshots():
    """加载历史快照"""
    f = DATA_DIR / "snapshots.json"
    if f.exists():
        with open(f, "r", encoding="utf-8") as fp:
            return json.load(fp)
    return []


def save_snapshots(snapshots):
    """保存快照"""
    with open(DATA_DIR / "snapshots.json", "w", encoding="utf-8") as fp:
        json.dump(snapshots, fp, ensure_ascii=False, indent=2)


def main():
    now = datetime.now()
    print(f"采集时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    hot_rank = fetch_hot_rank()
    popularity = fetch_popularity()
    sectors = fetch_sectors()

    if not hot_rank:
        print("热榜数据为空，跳过")
        return

    # 合并人气排名数据到热榜
    merged_count = 0
    for stock in hot_rank:
        code = stock["code"]
        if code in popularity:
            pop = popularity[code]
            stock["board_info"] = pop["board_info"]
            stock["board_reason"] = pop["board_reason"]
            # 用人气排名的真实价格覆盖热榜的0
            if pop["price"] and pop["price"] != "0":
                try:
                    stock["price"] = float(pop["price"])
                except (ValueError, TypeError):
                    pass
            stock["market_cap"] = pop["market_cap"]
            merged_count += 1
    print(f"热榜: {len(hot_rank)} 条, 板块: {len(sectors)} 条, 合并人气数据: {merged_count} 条")

    # 获取东方财富数据（今日浏览排名 + 换手率）- 覆盖全部热榜股票
    top_codes = [s["code"] for s in hot_rank]
    em_data = fetch_eastmoney_data(top_codes)
    for stock in hot_rank:
        code = stock["code"]
        if code in em_data:
            stock["turnover"] = em_data[code]["turnover"]
            stock["browse_rank"] = em_data[code]["browse_rank"]
        else:
            stock["turnover"] = 0
            stock["browse_rank"] = 0

    current = {
        "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "同花顺热榜",
        "total": len(hot_rank),
        "data": hot_rank[:100]
    }
    with open(DATA_DIR / "current.json", "w", encoding="utf-8") as fp:
        json.dump(current, fp, ensure_ascii=False, indent=2)

    with open(DATA_DIR / "sectors.json", "w", encoding="utf-8") as fp:
        json.dump({
            "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "同花顺热榜",
            "data": sectors
        }, fp, ensure_ascii=False, indent=2)

    # 独立模块：获取板块龙头股（不影响主流程）
    ths_sector_names = [s["板块名称"] for s in sectors]
    sector_leaders = fetch_sector_leaders(ths_sector_names)
    with open(DATA_DIR / "sector_leaders.json", "w", encoding="utf-8") as fp:
        json.dump({
            "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "东方财富",
            "data": sector_leaders
        }, fp, ensure_ascii=False, indent=2)

    snapshots = load_snapshots()
    snap = {
        "time": now.strftime("%m-%d %H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "stocks": [
            {
                "rank": s["rank"],
                "code": s["code"],
                "name": s["name"],
                "price": s["price"],
                "change_pct": s["change_pct"],
                "hot_value": s["hot_value"],
                "board_info": s["board_info"],
                "board_reason": s["board_reason"],
                "market_cap": s["market_cap"],
                "turnover": s["turnover"],
                "browse_rank": s["browse_rank"],
            }
            for s in hot_rank[:50]
        ]
    }
    snapshots.append(snap)

    if len(snapshots) > 1440:
        snapshots = snapshots[-1440:]

    save_snapshots(snapshots)
    print(f"快照总数: {len(snapshots)}")


if __name__ == "__main__":
    main()
