#!/usr/bin/env python3
"""
采集同花顺热榜数据并保存为 JSON
数据来源: 同花顺官方API (dq.10jqka.com.cn + basic.10jqka.com.cn)
供 GitHub Actions 定时任务使用
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent))

from modules.config import DATA_DIR
from modules.hot_rank import fetch_hot_rank
from modules.skyrocket import fetch_skyrocket
from modules.popularity import fetch_popularity
from modules.eastmoney import fetch_eastmoney_data
from modules.sectors import fetch_sectors, dedup_sectors
from modules.sector_leaders import fetch_sector_leaders
from modules.snapshots import load_snapshots, save_snapshots
from modules.xueqiu import fetch_xueqiu_hot, save_xueqiu_data

def analyze_board_strength(hot_rank, sectors_data):
    """
    分析板块梯队强度
    返回: {板块名: {zt_count, total_in_rank, avg_hot, leaders: []}}
    """
    if not hot_rank or not sectors_data:
        return {}
    
    # 统计每个板块在热榜中的股票
    sector_stats = {}
    
    for stock in hot_rank[:50]:
        code = stock.get("code", "")
        name = stock.get("name", "")
        change_pct = stock.get("change_pct", 0)
        hot_value = stock.get("hot_value", "0")
        concept_tags = stock.get("concept_tags", [])
        
        # 判断是否涨停（涨幅>=9.9%）
        is_zt = change_pct >= 9.9
        
        for tag in concept_tags[:2]:  # 只取前2个概念
            if tag not in sector_stats:
                sector_stats[tag] = {
                    "name": tag,
                    "zt_count": 0,
                    "total_in_rank": 0,
                    "total_hot": 0,
                    "stocks": []
                }
            
            sector_stats[tag]["total_in_rank"] += 1
            try:
                sector_stats[tag]["total_hot"] += float(hot_value)
            except:
                pass
            
            if is_zt:
                sector_stats[tag]["zt_count"] += 1
            
            sector_stats[tag]["stocks"].append({
                "code": code,
                "name": name,
                "change_pct": change_pct,
                "hot_value": hot_value,
                "is_zt": is_zt
            })
    
    # 计算平均热度并排序
    for tag in sector_stats:
        count = sector_stats[tag]["total_in_rank"]
        sector_stats[tag]["avg_hot"] = sector_stats[tag]["total_hot"] / count if count > 0 else 0
        # 按涨幅排序股票
        sector_stats[tag]["stocks"].sort(key=lambda x: x["change_pct"], reverse=True)
    
    return sector_stats

def main():
    now = datetime.now()
    print(f"采集时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取同花顺热榜数据
    hot_rank = fetch_hot_rank()
    
    # 获取飙升榜数据
    skyrocket = fetch_skyrocket()
    
    # 获取同花顺人气数据（涨停原因等）
    popularity = fetch_popularity()
    
    # 获取板块数据
    sectors = fetch_sectors()
    
    # 获取雪球热股排名
    xueqiu_rank = {}
    try:
        xueqiu_rank = fetch_xueqiu_hot()
        if xueqiu_rank:
            save_xueqiu_data(xueqiu_rank)
            print(f"[雪球] 成功获取 {len(xueqiu_rank)} 只股票数据")
    except Exception as e:
        print(f"[雪球] 获取失败: {e}")
    
    if not hot_rank:
        print("错误: 热榜数据为空，跳过本次采集")
        return
    
    print(f"[同花顺] 热榜: {len(hot_rank)} 只股票")
    
    # 合并人气排名数据到热榜
    merged_count = 0
    for stock in hot_rank:
        code = stock.get("code", "")
        if code in popularity:
            pop = popularity[code]
            stock["board_info"] = pop.get("board_info", "")
            stock["board_reason"] = pop.get("board_reason", "")
            stock["market_cap"] = pop.get("market_cap", 0)
            merged_count += 1
    
    print(f"[同花顺] 合并人气数据: {merged_count} 只")
    
    # 合并雪球热股排名
    xq_count = 0
    for stock in hot_rank:
        code = stock.get("code", "")
        xq_key_sh = "SH" + code
        xq_key_sz = "SZ" + code
        if xq_key_sh in xueqiu_rank:
            stock["xueqiu_rank"] = xueqiu_rank[xq_key_sh]
            xq_count += 1
        elif xq_key_sz in xueqiu_rank:
            stock["xueqiu_rank"] = xueqiu_rank[xq_key_sz]
            xq_count += 1
        else:
            stock["xueqiu_rank"] = 0
    
    print(f"[雪球] 热股匹配: {xq_count}/{len(hot_rank)} 只")
    
    # 获取东方财富数据
    print("[东财] 正在获取数据...")
    em_data = fetch_eastmoney_data([])
    
    em_matched = 0
    for stock in hot_rank:
        code = stock.get("code", "")
        if code in em_data:
            em_matched += 1
            stock["turnover"] = em_data[code].get("turnover", 0)
            stock["browse_rank"] = em_data[code].get("browse_rank", 0)
        else:
            stock["turnover"] = stock.get("turnover", 0)
            stock["browse_rank"] = stock.get("browse_rank", 0)
    
    print(f"[东财] 匹配: {em_matched}/{len(hot_rank)} 只")
    
    # 保存当前数据
    current = {
        "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "同花顺热榜",
        "total": len(hot_rank),
        "data": hot_rank[:100]
    }
    
    current_file = DATA_DIR / "current.json"
    with open(current_file, "w", encoding="utf-8") as fp:
        json.dump(current, fp, ensure_ascii=False, indent=2)
    
    print(f"[保存] current.json ({len(hot_rank)} 条)")
    
    # 保存飙升榜数据
    if skyrocket:
        skyrocket_data = {
            "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "同花顺飙升榜",
            "total": len(skyrocket),
            "data": skyrocket[:50]
        }
        skyrocket_file = DATA_DIR / "skyrocket.json"
        with open(skyrocket_file, "w", encoding="utf-8") as fp:
            json.dump(skyrocket_data, fp, ensure_ascii=False, indent=2)
        print(f"[保存] skyrocket.json ({len(skyrocket)} 条)")
    
    # 板块去重合并
    sectors = dedup_sectors(sectors)
    sectors_file = DATA_DIR / "sectors.json"
    with open(sectors_file, "w", encoding="utf-8") as fp:
        json.dump({
            "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "同花顺热榜",
            "data": sectors
        }, fp, ensure_ascii=False, indent=2)
    
    print(f"[保存] sectors.json ({len(sectors)} 条)")
    
    # 分析板块梯队强度
    board_strength = analyze_board_strength(hot_rank, sectors)
    if board_strength:
        # 按涨停数量排序
        sorted_sectors = sorted(board_strength.values(), key=lambda x: (x["zt_count"], x["total_in_rank"]), reverse=True)
        strength_file = DATA_DIR / "board_strength.json"
        with open(strength_file, "w", encoding="utf-8") as fp:
            json.dump({
                "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "data": sorted_sectors[:30]  # 只保留前30个板块
            }, fp, ensure_ascii=False, indent=2)
        print(f"[保存] board_strength.json ({len(sorted_sectors)} 个板块)")
    
    # 获取板块龙头股
    sector_names = [s.get("板块名称", "") for s in sectors if s.get("板块名称")]
    sector_leaders = fetch_sector_leaders(hot_rank, sector_names)
    leaders_file = DATA_DIR / "sector_leaders.json"
    with open(leaders_file, "w", encoding="utf-8") as fp:
        json.dump({
            "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "同花顺热榜",
            "data": sector_leaders
        }, fp, ensure_ascii=False, indent=2)
    
    print(f"[保存] sector_leaders.json ({len(sector_leaders)} 个板块)")
    
    # 验证价格数据
    zero_price_count = sum(1 for s in hot_rank[:10] if s.get("price", 0) == 0)
    if zero_price_count >= 5:
        print(f"警告: 前10只股票中有 {zero_price_count} 只价格为0")
    
    # 保存快照数据
    snapshots = load_snapshots()
    snap = {
        "time": now.strftime("%m-%d %H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "stocks": [
            {
                "rank": s.get("rank", 0),
                "code": s.get("code", ""),
                "name": s.get("name", ""),
                "price": s.get("price", 0),
                "change_pct": s.get("change_pct", 0),
                "hot_value": s.get("hot_value", 0),
                "turnover": s.get("turnover", 0),
                "board_info": s.get("board_info", ""),
                "board_reason": s.get("board_reason", ""),
                "concept_tags": s.get("concept_tags", []),
            }
            for s in hot_rank[:50]
        ]
    }
    
    # 验证：如果快照中价格全为0，不保存
    valid_prices = sum(1 for s in snap["stocks"] if s["price"] > 0)
    if valid_prices < 5:
        print(f"错误: 快照中仅 {valid_prices}/50 只股票有有效价格，跳过保存")
    else:
        snapshots.append(snap)
        # 保留最近1440条（30天，每30分钟一条）
        if len(snapshots) > 1440:
            snapshots = snapshots[-1440:]
        save_snapshots(snapshots)
        print(f"[保存] snapshots.json ({valid_prices}/50 有效价格, 共 {len(snapshots)} 条快照)")
    
    print(f"完成: {now.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()