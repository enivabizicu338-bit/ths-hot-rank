"""
配置文件
"""
from pathlib import Path

# 数据目录
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# API配置 - 同花顺热榜新API（2026-05更新）
THS_HOT_RANK_URL = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=hour&list_type=normal"
THS_SKYROCKET_URL = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=hour&list_type=skyrocket"
THS_POPULARITY_URL = "https://basic.10jqka.com.cn/api/stockph/popularityrank"

# 板块API
THS_PLATE_CONCEPT_URL = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/plate?type=concept"
THS_PLATE_INDUSTRY_URL = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/plate?type=industry"

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://eq.10jqka.com.cn/",
}