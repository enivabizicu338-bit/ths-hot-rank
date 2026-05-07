"""
获取同花顺热门概念板块 + 板块名称去重合并
"""

from .config import session


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


def dedup_sectors(sectors):
    """合并相似板块名称，去除重复板块

    规则:
    - 如果一个名称是另一个名称的子串，合并到更长的名称
    - 合并时保留涨跌幅绝对值更大的那个板块的数据
    - 已知合并对:
      - "人形机器人" 和 "机器人概念" -> 保留 "机器人概念"
      - "AI应用" 和 "人工智能" -> 保留 "人工智能"
    """
    if not sectors:
        return sectors

    # 手动指定的合并规则（优先级最高）
    manual_merge = {
        "人形机器人": "机器人概念",
        "AI应用": "人工智能",
    }

    # 按板块名称建立索引
    name_to_sector = {}
    for s in sectors:
        name = s["板块名称"]
        name_to_sector[name] = dict(s)  # 深拷贝

    # 第一轮: 应用手动合并规则
    for src, dst in manual_merge.items():
        if src in name_to_sector and dst in name_to_sector:
            # 保留涨跌幅绝对值更大的
            if abs(name_to_sector[src]["涨跌幅"]) > abs(name_to_sector[dst]["涨跌幅"]):
                name_to_sector[dst] = name_to_sector[src]
            del name_to_sector[src]
        elif src in name_to_sector:
            # dst 不存在，直接重命名
            name_to_sector[dst] = name_to_sector.pop(src)

    # 第二轮: 通用子串匹配去重
    names = sorted(name_to_sector.keys(), key=len, reverse=True)  # 长名在前
    merged = set()
    result_map = {}

    for name in names:
        if name in merged:
            continue
        result_map[name] = name_to_sector[name]
        # 检查是否有更短的名称是当前名称的子串
        for other in names:
            if other == name or other in merged:
                continue
            # 如果 other 是 name 的子串，或者 name 是 other 的子串
            if other in name or name in other:
                # 保留更长的名称，合并数据
                longer = name if len(name) >= len(other) else other
                shorter = other if longer == name else name
                if abs(name_to_sector[shorter]["涨跌幅"]) > abs(result_map[longer]["涨跌幅"]):
                    result_map[longer] = name_to_sector[shorter]
                merged.add(shorter)

    result = list(result_map.values())
    # 按涨跌幅降序排列
    result.sort(key=lambda x: x["涨跌幅"], reverse=True)
    print(f"板块去重: {len(sectors)} -> {len(result)} 个板块")
    return result
