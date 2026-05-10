#!/usr/bin/env python3
"""
策略引擎 - 定义推荐策略因子、权重、计算逻辑
支持动态权重调整（策略进化）
"""
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
STRATEGY_FILE = os.path.join(DATA_DIR, 'strategy_weights.json')

# 默认策略定义
DEFAULT_STRATEGIES = {
    "hot_sector_boost": {
        "name": "热门板块加成",
        "description": "所属概念板块在板块排行中涨幅前列，板块热度传导到个股",
        "weight": 30,
        "max_score": 30,
        "logic": "取个股所属概念板块中涨幅最大的一个。板块涨幅>=4%得30分，>=3%得25分，>=2%得20分，>=1%得12分，>0%得6分。同时如果板块在排行前10名，额外加5分。",
        "category": "板块共振",
        "success_rate": None,
        "total_backtests": 0,
        "correct_predictions": 0,
        "evolution_log": []
    },
    "hot_rank": {
        "name": "热榜排名",
        "description": "同花顺热榜排名反映市场关注度，排名越靠前关注度越高",
        "weight": 20,
        "max_score": 20,
        "logic": "TOP3得20分，TOP10得16分，TOP20得12分，TOP50得8分，TOP100得4分",
        "category": "市场关注度",
        "success_rate": None,
        "total_backtests": 0,
        "correct_predictions": 0,
        "evolution_log": []
    },
    "momentum": {
        "name": "涨跌动量",
        "description": "当日涨跌幅反映资金推动力度，涨停说明买盘极强",
        "weight": 20,
        "max_score": 20,
        "logic": "涨停(>=9.9%)得20分，>=7%得16分，>=5%得13分，>=3%得9分，>=0%得4分，<0%得0分",
        "category": "资金推动",
        "success_rate": None,
        "total_backtests": 0,
        "correct_predictions": 0,
        "evolution_log": []
    },
    "skyrocket": {
        "name": "飙升榜上榜",
        "description": "飙升榜反映关注度急速上升，说明有新增资金关注",
        "weight": 15,
        "max_score": 15,
        "logic": "飙升榜TOP5得15分，TOP15得12分，TOP30得9分，其他上榜得5分",
        "category": "市场关注度",
        "success_rate": None,
        "total_backtests": 0,
        "correct_predictions": 0,
        "evolution_log": []
    },
    "news_heat": {
        "name": "新闻热度关联",
        "description": "新闻中出现股票名称或所属概念，说明有事件驱动",
        "weight": 15,
        "max_score": 15,
        "logic": "新闻热词匹配股票名或概念标签。匹配>=3个词得15分，>=2个得11分，>=1个得7分",
        "category": "事件驱动",
        "success_rate": None,
        "total_backtests": 0,
        "correct_predictions": 0,
        "evolution_log": []
    },
    "turnover": {
        "name": "换手率活跃度",
        "description": "换手率反映交投活跃程度，过低无资金关注，过高可能见顶",
        "weight": 10,
        "max_score": 10,
        "logic": "5-15%得10分（最佳区间），15-25%得7分，3-5%得5分，>25%得3分（可能见顶），<3%得1分",
        "category": "资金推动",
        "success_rate": None,
        "total_backtests": 0,
        "correct_predictions": 0,
        "evolution_log": []
    },
    "concept_richness": {
        "name": "概念题材丰富度",
        "description": "拥有多个热门概念标签的股票更容易受到板块轮动带动",
        "weight": 5,
        "max_score": 5,
        "logic": "概念标签>=4个得5分，>=3个得4分，>=2个得3分，>=1个得1分",
        "category": "板块共振",
        "success_rate": None,
        "total_backtests": 0,
        "correct_predictions": 0,
        "evolution_log": []
    }
}


def load_strategies():
    """加载策略配置（含动态权重）"""
    try:
        with open(STRATEGY_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        # 合并默认策略（防止新增策略丢失）
        for key, val in DEFAULT_STRATEGIES.items():
            if key not in saved:
                saved[key] = val
            else:
                # 保留动态权重和统计数据，更新描述
                saved[key]['name'] = val['name']
                saved[key]['description'] = val['description']
                saved[key]['logic'] = val['logic']
                saved[key]['max_score'] = val['max_score']
                saved[key]['category'] = val['category']
        return saved
    except:
        return dict(DEFAULT_STRATEGIES)


def save_strategies(strategies):
    """保存策略配置"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STRATEGY_FILE, 'w', encoding='utf-8') as f:
        json.dump(strategies, f, ensure_ascii=False, indent=2)


def get_strategy_summary():
    """获取策略概览（用于前端展示）"""
    strategies = load_strategies()
    result = []
    total_weight = sum(s.get('weight', 0) for s in strategies.values())

    for key, s in strategies.items():
        sr = s.get('success_rate')
        result.append({
            'key': key,
            'name': s['name'],
            'description': s['description'],
            'weight': s['weight'],
            'weight_pct': round(s['weight'] / total_weight * 100, 1) if total_weight else 0,
            'max_score': s['max_score'],
            'logic': s['logic'],
            'category': s['category'],
            'success_rate': sr,
            'total_backtests': s.get('total_backtests', 0),
            'correct_predictions': s.get('correct_predictions', 0),
            'evolution_count': len(s.get('evolution_log', [])),
        })

    return {
        'strategies': result,
        'total_weight': total_weight,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }


def update_strategy_weights(feedback):
    """
    根据回测反馈更新策略权重（策略进化）
    feedback: {factor_key: {'predicted_up': bool, 'actual_up': bool, 'delta': float}, ...}
    """
    strategies = load_strategies()
    evolution_records = []

    for key, fb in feedback.items():
        if key not in strategies:
            continue

        s = strategies[key]
        s['total_backtests'] = s.get('total_backtests', 0) + 1

        predicted_up = fb.get('predicted_up', False)
        actual_up = fb.get('actual_up', False)
        delta = fb.get('delta', 0)

        # 判断这个因子的预测是否正确
        # 如果因子得分高（预测上涨）且实际上涨 → 正确
        # 如果因子得分高但实际下跌 → 错误
        if predicted_up and actual_up:
            s['correct_predictions'] = s.get('correct_predictions', 0) + 1
            correct = True
        elif predicted_up and not actual_up:
            correct = False
        elif not predicted_up and not actual_up:
            s['correct_predictions'] = s.get('correct_predictions', 0) + 1
            correct = True
        else:
            correct = False

        # 更新成功率
        total = s['total_backtests']
        correct_count = s['correct_predictions']
        s['success_rate'] = round(correct_count / total * 100, 1) if total > 0 else None

        # 根据成功率调整权重（微调，每次±2）
        old_weight = s['weight']
        if total >= 3:  # 至少3次回测才调整
            if s['success_rate'] >= 60:
                # 成功率高，小幅增加权重
                new_weight = min(old_weight + 2, s['max_score'])
            elif s['success_rate'] <= 40:
                # 成功率低，小幅降低权重
                new_weight = max(old_weight - 2, 1)
            else:
                new_weight = old_weight

            if new_weight != old_weight:
                s['weight'] = new_weight
                direction = '上调' if new_weight > old_weight else '下调'
                log_entry = {
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'old_weight': old_weight,
                    'new_weight': new_weight,
                    'success_rate': s['success_rate'],
                    'reason': f"成功率{s['success_rate']}%，{direction}权重"
                }
                s['evolution_log'].append(log_entry)
                evolution_records.append({
                    'strategy': s['name'],
                    **log_entry
                })

    save_strategies(strategies)
    return evolution_records
