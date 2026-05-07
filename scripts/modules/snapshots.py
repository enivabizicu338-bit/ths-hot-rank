"""
历史快照加载与保存
"""

import json

from .config import DATA_DIR


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
