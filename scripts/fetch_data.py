#!/usr/bin/env python3
"""
采集同花顺热榜数据并保存为 JSON
数据来源: 同花顺官方API (dq.10jqka.com.cn)
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
                })
            return stocks
        else:
            print(f"热榜API返回异常: {data}")
            return []
    except Exception as e:
        print(f"热榜获取失败: {e}")
        return []


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
    sectors = fetch_sectors()

    if not hot_rank:
        print("热榜数据为空，跳过")
        return

    print(f"热榜: {len(hot_rank)} 条, 板块: {len(sectors)} 条")

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
