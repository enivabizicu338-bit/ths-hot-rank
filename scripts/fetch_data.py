#!/usr/bin/env python3
"""
采集同花顺热榜数据并保存为 JSON
数据来源: 同花顺官方API (dq.10jqka.com.cn + basic.10jqka.com.cn)
供 GitHub Actions 定时任务使用
"""

import json
from datetime import datetime

from modules.config import DATA_DIR
from modules.hot_rank import fetch_hot_rank
from modules.popularity import fetch_popularity
from modules.eastmoney import fetch_eastmoney_data
from modules.sectors import fetch_sectors, dedup_sectors
from modules.sector_leaders import fetch_sector_leaders
from modules.snapshots import load_snapshots, save_snapshots


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

    # 获取东方财富数据（今日浏览排名 + 换手率 + 实时价格 + 涨跌幅）- 覆盖全部热榜股票
    top_codes = [s["code"] for s in hot_rank]
    em_data = fetch_eastmoney_data(top_codes)
    price_count = 0
    for stock in hot_rank:
        code = stock["code"]
        if code in em_data:
            stock["turnover"] = em_data[code]["turnover"]
            stock["browse_rank"] = em_data[code]["browse_rank"]
            # 用东财实时价格覆盖（优先级最高）
            if em_data[code]["price"] > 0:
                stock["price"] = em_data[code]["price"]
                price_count += 1
            # 用东财实时涨跌幅覆盖（同花顺热榜的涨跌幅可能延迟）
            if em_data[code]["change_pct"] != 0:
                stock["change_pct"] = em_data[code]["change_pct"]
        else:
            stock["turnover"] = 0
            stock["browse_rank"] = 0
    print(f"东财实时价格覆盖: {price_count}/{len(hot_rank)} 只")

    current = {
        "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "同花顺热榜",
        "total": len(hot_rank),
        "data": hot_rank[:100]
    }
    with open(DATA_DIR / "current.json", "w", encoding="utf-8") as fp:
        json.dump(current, fp, ensure_ascii=False, indent=2)

    # 板块去重合并
    sectors = dedup_sectors(sectors)

    with open(DATA_DIR / "sectors.json", "w", encoding="utf-8") as fp:
        json.dump({
            "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "同花顺热榜",
            "data": sectors
        }, fp, ensure_ascii=False, indent=2)

    # 获取板块龙头股（基于同花顺热榜数据，100%准确匹配）
    sector_names = [s["板块名称"] for s in sectors]
    sector_leaders = fetch_sector_leaders(hot_rank, sector_names)
    with open(DATA_DIR / "sector_leaders.json", "w", encoding="utf-8") as fp:
        json.dump({
            "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "同花顺热榜",
            "data": sector_leaders
        }, fp, ensure_ascii=False, indent=2)

    # 验证价格数据 - 如果前10只股票价格都为0，说明数据获取有问题
    zero_price_count = sum(1 for s in hot_rank[:10] if s.get("price", 0) == 0)
    if zero_price_count >= 5:
        print(f"警告: 前10只股票中有 {zero_price_count} 只价格为0，数据可能不完整")

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

    # 再次验证：如果快照中价格全为0，不保存（避免污染历史数据）
    valid_prices = sum(1 for s in snap["stocks"] if s["price"] > 0)
    if valid_prices < 5:
        print(f"错误: 快照中仅 {valid_prices}/50 只股票有有效价格，跳过保存")
    else:
        snapshots.append(snap)
        if len(snapshots) > 1440:
            snapshots = snapshots[-1440:]
        save_snapshots(snapshots)
        print(f"快照已保存: 有效价格 {valid_prices}/50, 快照总数: {len(snapshots)}")


if __name__ == "__main__":
    main()
