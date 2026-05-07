#!/usr/bin/env python3
"""
采集同花顺热榜数据并保存为 JSON
供 GitHub Actions 定时任务使用
"""

import akshare as ak
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def fetch_hot_rank():
    """获取热榜"""
    try:
        df = ak.stock_hot_rank_em()
        df.columns = ["rank", "code", "name", "price", "change_amount", "change_pct"]
        return df.to_dict("records")
    except Exception as e:
        print(f"热榜获取失败: {e}")
        return []


def fetch_sectors():
    """获取热门板块"""
    try:
        df = ak.stock_board_concept_name_em()
        return df.head(20).to_dict("records")
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

    # 获取数据
    hot_rank = fetch_hot_rank()
    sectors = fetch_sectors()

    if not hot_rank:
        print("热榜数据为空，跳过")
        return

    print(f"热榜: {len(hot_rank)} 条, 板块: {len(sectors)} 条")

    # 保存当前热榜
    current = {
        "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(hot_rank),
        "data": hot_rank[:100]
    }
    with open(DATA_DIR / "current.json", "w", encoding="utf-8") as fp:
        json.dump(current, fp, ensure_ascii=False, indent=2)

    # 保存板块
    with open(DATA_DIR / "sectors.json", "w", encoding="utf-8") as fp:
        json.dump({
            "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "data": sectors
        }, fp, ensure_ascii=False, indent=2)

    # 添加快照
    snapshots = load_snapshots()
    snap = {
        "time": now.strftime("%m-%d %H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "stocks": [
            {
                "rank": int(s["rank"]),
                "code": s["code"],
                "name": s["name"],
                "price": float(s["price"]),
                "change_pct": float(s["change_pct"]),
            }
            for s in hot_rank[:50]
        ]
    }
    snapshots.append(snap)

    # 保留最近 200 个快照（约 4 天）
    if len(snapshots) > 200:
        snapshots = snapshots[-200:]

    save_snapshots(snapshots)
    print(f"快照总数: {len(snapshots)}")


if __name__ == "__main__":
    main()
