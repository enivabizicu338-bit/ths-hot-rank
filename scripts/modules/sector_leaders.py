#!/usr/bin/env python3
"""
板块龙头股获取
"""

def fetch_sector_leaders(hot_rank, sector_names):
    """
    从热榜数据中找出每个板块的龙头股
    hot_rank: 热榜股票列表
    sector_names: 板块名称列表
    返回: {板块名称: [{code, name, hot_value, rank}, ...], ...}
    """
    result = {}
    
    for sector_name in sector_names:
        if not sector_name:
            continue
        
        # 找出属于该板块的股票
        leaders = []
        for stock in hot_rank:
            concept_tags = stock.get("concept_tags", [])
            # 检查股票的概念标签是否包含该板块
            if any(sector_name in tag or tag in sector_name for tag in concept_tags):
                leaders.append({
                    "code": stock.get("code", ""),
                    "name": stock.get("name", ""),
                    "hot_value": stock.get("hot_value", 0),
                    "rank": stock.get("rank", 999)
                })
        
        # 按排名排序，取前3只
        leaders.sort(key=lambda x: x["rank"])
        result[sector_name] = leaders[:3]
    
    return result


if __name__ == "__main__":
    import json
    # 测试数据
    hot_rank = [
        {"code": "000001", "name": "平安银行", "hot_value": 10000, "rank": 1, "concept_tags": ["银行", "金融科技"]},
        {"code": "000002", "name": "万科A", "hot_value": 9000, "rank": 2, "concept_tags": ["房地产", "物业管理"]},
    ]
    sectors = ["银行", "房地产"]
    result = fetch_sector_leaders(hot_rank, sectors)
    print(json.dumps(result, ensure_ascii=False, indent=2))