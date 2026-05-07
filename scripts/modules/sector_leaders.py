"""
获取板块龙头股 - 基于同花顺热榜数据（纯同花顺数据源，100%准确匹配）
"""


def fetch_sector_leaders(hot_rank_stocks, sector_names):
    """根据同花顺热榜数据获取各板块龙头股

    Args:
        hot_rank_stocks: 热榜股票列表，每只股票包含 concept_tags 和 hot_value 字段
        sector_names: 板块名称列表（来自 sectors.json）

    Returns:
        dict: {sector_name: [{code, name, hot_value, change_pct}, ...]}
              每个板块取热度最高的前3只股票
    """
    print("开始获取板块龙头股（同花顺热榜数据源）...")

    # 建立板块名称 -> 股票列表的映射
    sector_stocks = {name: [] for name in sector_names}

    for stock in hot_rank_stocks:
        concept_tags = stock.get("concept_tags", [])
        if not concept_tags:
            continue
        for tag in concept_tags:
            if tag in sector_stocks:
                sector_stocks[tag].append({
                    "code": stock["code"],
                    "name": stock["name"],
                    "hot_value": stock.get("hot_value", "0"),
                    "change_pct": stock.get("change_pct", 0),
                })

    # 对每个板块按 hot_value 降序排列，取前3
    leaders_map = {}
    matched = 0
    for name in sector_names:
        stocks = sector_stocks.get(name, [])
        if stocks:
            # hot_value 可能是字符串或数字，统一转换为 float 排序
            for s in stocks:
                try:
                    s["hot_value"] = float(s["hot_value"])
                except (ValueError, TypeError):
                    s["hot_value"] = 0.0
            stocks.sort(key=lambda x: x["hot_value"], reverse=True)
            leaders_map[name] = stocks[:3]
            matched += 1
        else:
            leaders_map[name] = []

    print(f"板块龙头股: 匹配 {matched}/{len(sector_names)} 个板块")
    return leaders_map
