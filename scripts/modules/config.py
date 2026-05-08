"""
全局配置: 数据目录、请求头、会话对象
"""

import requests
from pathlib import Path

# 数据目录：相对于项目根目录 (ths-gh-pages)
# 脚本在 scripts/ 或 scripts/modules/ 下运行，需要找到正确的数据目录
_SCRIPT_DIR = Path(__file__).parent
if _SCRIPT_DIR.name == "modules":
    # 当前文件在 scripts/modules/ 下
    DATA_DIR = _SCRIPT_DIR.parent.parent / "data"
else:
    # 当前文件在 scripts/ 下
    DATA_DIR = _SCRIPT_DIR.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; Pixel 3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
    "Referer": "https://eq.10jqka.com.cn/frontend/thsTopRank/index.html",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)
