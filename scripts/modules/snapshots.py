#!/usr/bin/env python3
"""
快照数据管理
"""
import json
from .config import DATA_DIR

def load_snapshots():
    """
    加载历史快照数据
    """
    snapshots_file = DATA_DIR / "snapshots.json"
    if snapshots_file.exists():
        try:
            with open(snapshots_file, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception as e:
            print(f"[快照] 加载失败: {e}")
    return []


def save_snapshots(snapshots):
    """
    保存快照数据
    """
    snapshots_file = DATA_DIR / "snapshots.json"
    try:
        with open(snapshots_file, "w", encoding="utf-8") as fp:
            json.dump(snapshots, fp, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[快照] 保存失败: {e}")
        return False