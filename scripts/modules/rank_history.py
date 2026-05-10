#!/usr/bin/env python3
"""
排名历史分析 - 从快照中提取股票排名走势
"""
import json
import os
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')


def load_snapshots():
    """加载快照数据"""
    filepath = os.path.join(DATA_DIR, 'snapshots.json')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def get_top_stocks_rank_history(top_n=30, max_snapshots=None):
    """
    获取TOP N股票的排名历史走势

    参数:
        top_n: 取最近快照中排名前N的股票
        max_snapshots: 最多使用多少条快照(默认全部)

    返回:
        {
            "time_labels": ["05-07 09:30", "05-07 10:00", ...],
            "stocks": [
                {
                    "code": "600522",
                    "name": "中天科技",
                    "data": [1, 1, 2, 3, null, null, 5, ...],
                    "in_rank_count": 25,
                    "best_rank": 1,
                    "avg_rank": 3.5,
                    "current_rank": 5
                },
                ...
            ]
        }
    """
    snapshots = load_snapshots()
    if not snapshots:
        return {"time_labels": [], "stocks": []}

    if max_snapshots:
        snapshots = snapshots[-max_snapshots:]

    # 1. 找出最近一次快照中排名前top_n的股票
    latest = snapshots[-1] if snapshots else {}
    latest_stocks = latest.get('stocks', [])

    target_codes = set()
    for s in latest_stocks[:top_n]:
        target_codes.add(s.get('code', ''))

    # 2. 也找出历史上经常进入前30的股票（补充）
    stock_appear_count = defaultdict(int)
    stock_name_map = {}
    for snap in snapshots:
        for s in snap.get('stocks', []):
            code = s.get('code', '')
            if s.get('rank', 999) <= top_n:
                stock_appear_count[code] += 1
                stock_name_map[code] = s.get('name', '')

    # 补充历史上榜次数>=5次但不在当前TOP30的股票
    for code, count in stock_appear_count.items():
        if count >= 5 and code not in target_codes:
            target_codes.add(code)

    # 限制最多30只
    if len(target_codes) > 30:
        def sort_key(code):
            latest_rank = 999
            for s in latest_stocks:
                if s.get('code') == code:
                    latest_rank = s.get('rank', 999)
                    break
            return (latest_rank, -stock_appear_count.get(code, 0))
        target_codes = sorted(target_codes, key=sort_key)[:30]

    # 3. 构建时间标签和排名数据
    time_labels = []
    for snap in snapshots:
        time_str = snap.get('time', '')
        date_str = snap.get('date', '')
        if date_str and time_str:
            time_labels.append(f"{time_str}")
        else:
            time_labels.append(time_str)

    # 4. 为每只目标股票构建排名序列
    stocks_data = []
    for code in target_codes:
        name = stock_name_map.get(code, code)
        rank_series = []
        in_rank_count = 0
        best_rank = 999
        rank_sum = 0

        for snap in snapshots:
            found = False
            for s in snap.get('stocks', []):
                if s.get('code') == code:
                    rank = s.get('rank', None)
                    rank_series.append(rank)
                    if rank:
                        in_rank_count += 1
                        best_rank = min(best_rank, rank)
                        rank_sum += rank
                    found = True
                    break
            if not found:
                rank_series.append(None)

        # 最新排名
        current_rank = None
        for s in latest_stocks:
            if s.get('code') == code:
                current_rank = s.get('rank')
                break

        avg_rank = round(rank_sum / in_rank_count, 1) if in_rank_count > 0 else None

        stocks_data.append({
            "code": code,
            "name": name,
            "data": rank_series,
            "in_rank_count": in_rank_count,
            "best_rank": best_rank if best_rank < 999 else None,
            "avg_rank": avg_rank,
            "current_rank": current_rank,
        })

    # 按当前排名排序
    stocks_data.sort(key=lambda x: x['current_rank'] or 999)

    return {
        "time_labels": time_labels,
        "stocks": stocks_data,
        "snapshot_count": len(snapshots),
    }


if __name__ == '__main__':
    result = get_top_stocks_rank_history(top_n=30)
    print(f"快照数: {result['snapshot_count']}")
    print(f"时间点: {len(result['time_labels'])}")
    print(f"股票数: {len(result['stocks'])}")
    for s in result['stocks'][:5]:
        print(f"  {s['name']}({s['code']}) 当前#{s['current_rank']} 上榜{s['in_rank_count']}次 最佳#{s['best_rank']}")
