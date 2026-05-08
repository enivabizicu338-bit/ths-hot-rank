"""
雪球热股榜数据获取模块 - 使用cookie认证
支持翻页获取全部沪深热股
"""

import json
import requests
from pathlib import Path
from datetime import datetime

# 数据目录
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# 雪球API
XUEQIU_API = "https://stock.xueqiu.com/v5/stock/hot_stock/list.json"

# Cookie（从浏览器获取）
COOKIE = "xq_a_token=0b6d260a5333284ddd41e07bd185f7392f567236; xqat=0b6d260a5333284ddd41e07bd185f7392f567236; xq_r_token=865b12c689ce7a8fd47556c8eaaf2d2e6361c23b; xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOi0xLCJpc3MiOiJ1YyIsImV4cCI6MTc3OTc1ODU4OCwiY3RtIjoxNzc4MjE0NTkyMjU4LCJjaWQiOiJkOWQwbjRBWnVwIn0.A6UUe4Ah6P1Z_iBuqRw5KdjP1K5oysIu7ZXfrkHeYUHtQP_bQrdkICQfrMwqRlSXGjvVkNJvkZfa6SKt6aXq2vnj4KEjs0LIv93-fJiNlj4xTslDf_L_K3axCTzSy_5tkF4tpQoK10qC-4y1wrnF3kMU5dxL3fYq2PQlW6PLpXQJuONig27JipEZZIlPI2D9DjdkQRoOC3RrzdyCGt7ZkhLLKTPrwJTCGyGyKzffCqwiD5ztauCeurudmGZaSWEWotGVHUQ5SMuO-o94dIyv89jfMBUHTV68mgd5dTJ72omTgjQUjIwTSnhHPOphSkS2B85lVXkNYmg4LtLYPHGxvw; cookiesu=281778214619023; u=281778214619023; device_id=12c9cf5c5d56611c0d8fd5b31f2626be"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://xueqiu.com/hq",
    "Accept": "application/json, text/plain, */*",
    "Cookie": COOKIE,
}


def fetch_xueqiu_hot(max_pages=3):
    """
    获取雪球热股榜数据（沪深），支持翻页
    返回: {code: rank} 映射
    """
    all_items = []

    for page in range(1, max_pages + 1):
        params = {
            "page": page,
            "size": 50,
            "_type": 18,  # 沪深
            "type": 10,
            "include": 1
        }

        try:
            response = requests.get(XUEQIU_API, params=params, headers=HEADERS, timeout=10)
            data = response.json()

            if "error_code" in data and data.get("error_code"):
                print(f"[雪球] API错误: {data.get('error_description')}")
                break

            items = data.get("data", {}).get("items", [])
            if not items:
                break

            all_items.extend(items)
            print(f"[雪球] 第{page}页获取 {len(items)} 条")

            # 如果返回不足50条，说明没有更多了
            if len(items) < 50:
                break

        except Exception as e:
            print(f"[雪球] 第{page}页请求失败: {e}")
            break

    # 构建纯沪深排名映射 {code: rank}
    rank_map = {}
    for item in all_items:
        symbol = item.get("symbol", "")
        if symbol.startswith("SH") or symbol.startswith("SZ"):
            if symbol not in rank_map:
                rank_map[symbol] = len(rank_map) + 1

    print(f"[雪球] 共获取 {len(rank_map)} 条纯沪深热股")
    return rank_map


def save_xueqiu_data(rank_map):
    """
    保存雪球热股数据到JSON
    """
    output = {
        "source": "xueqiu",
        "type": "沪深",
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(rank_map),
        "rank_map": rank_map
    }

    output_file = DATA_DIR / "xueqiu_hot.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[雪球] 已保存到 {output_file}")
    return rank_map


if __name__ == "__main__":
    print("=" * 50)
    print("雪球热股榜数据获取（沪深）")
    print("=" * 50)

    rank_map = fetch_xueqiu_hot(max_pages=3)
    if rank_map:
        save_xueqiu_data(rank_map)
        # 显示前15条
        sorted_stocks = sorted(rank_map.items(), key=lambda x: x[1])
        print(f"\n前15条:")
        for code, rank in sorted_stocks[:15]:
            print(f"  {rank:>2}. {code}")
    else:
        print("\n获取数据失败，cookie可能已过期")
