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
                    "guba_rank": 0,
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
    """获取东方财富数据 - 换手率 + 股吧人气排名"""
    em_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://data.eastmoney.com/",
    }
    em_session = requests.Session()
    em_session.headers.update(em_headers)

    result = {}  # code -> {turnover, guba_rank}

    # 1. 获取换手率（逐个查询50只股票）
    for code in codes:
        try:
            market = "1" if code.startswith("6") else "0"
            url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={market}.{code}&fields=f168"
            resp = em_session.get(url, timeout=8)
            d = resp.json().get("data", {})
            turnover = d.get("f168", 0) / 100 if d.get("f168") else 0
            result[code] = {"turnover": round(turnover, 2), "guba_rank": 0}
        except Exception:
            result[code] = {"turnover": 0, "guba_rank": 0}

    # 2. 获取股吧人气排名（批量获取前500）
    try:
        guba_map = {}
        for page in range(1, 6):
            url = f"https://push2.eastmoney.com/api/qt/clist/get?pn={page}&pz=100&po=1&np=1&fltt=2&invt=2&fid=f62&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12"
            resp = em_session.get(url, timeout=10)
            stocks = resp.json().get("data", {}).get("diff", [])
            for i, item in enumerate(stocks):
                rank = (page - 1) * 100 + i + 1
                guba_map[item["f12"]] = rank
        # 合并股吧排名
        guba_count = 0
        for code in codes:
            if code in guba_map:
                result[code]["guba_rank"] = guba_map[code]
                guba_count += 1
        print(f"东财数据: 换手率 {len(codes)} 条, 股吧排名匹配 {guba_count} 条")
    except Exception as e:
        print(f"股吧排名获取失败: {e}")

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
                    "领涨股票": "",
                })
            return sectors
        else:
            print(f"板块API返回异常: {data}")
            return []
    except Exception as e:
        print(f"板块获取失败: {e}")
        return []


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

    # 获取东方财富数据（换手率 + 股吧人气排名）
    top_codes = [s["code"] for s in hot_rank[:50]]
    em_data = fetch_eastmoney_data(top_codes)
    for stock in hot_rank[:50]:
        code = stock["code"]
        if code in em_data:
            stock["turnover"] = em_data[code]["turnover"]
            stock["guba_rank"] = em_data[code]["guba_rank"]
        else:
            stock["turnover"] = 0
            stock["guba_rank"] = 0

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
                "guba_rank": s["guba_rank"],
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
