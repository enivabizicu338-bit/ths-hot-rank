#!/usr/bin/env python3
"""
归因分析模块 - 事前归因 + 事后归因 + 对比优化
"""
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
ATTRIBUTION_FILE = os.path.join(DATA_DIR, 'attributions.json')


def _load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def pre_attribution(stock, factor_scores, strategies):
    """
    事前归因：在推荐时记录每只股票的因子得分和预测逻辑

    参数:
        stock: 股票数据
        factor_scores: {factor_key: score} 各因子得分
        strategies: 策略配置

    返回:
        {
            'code': '002281',
            'name': '光迅科技',
            'pre_attribution': {
                'total_score': 85,
                'factors': [
                    {
                        'key': 'hot_sector_boost',
                        'name': '热门板块加成',
                        'score': 25,
                        'max_score': 30,
                        'prediction': '所属板块[共封装光学]涨幅3.29%，板块排名第4，预测板块热度将推动个股继续上涨',
                        'confidence': 'high'  # high/medium/low
                    },
                    ...
                ],
                'overall_prediction': '综合评分85分，热门板块+涨停+飙升榜多重利好共振，预测短期内继续上涨概率较高',
                'risk_factors': ['换手率偏高(18.5%)可能存在短期见顶风险'],
                'key_thesis': 'CPO概念板块强势领涨(第4名+3.29%)，个股涨停封板，资金关注度高'
            }
        }
    """
    code = stock.get('code', '')
    name = stock.get('name', '')
    concept_tags = stock.get('concept_tags', [])
    change_pct = stock.get('change_pct', 0) or 0
    turnover = stock.get('turnover', 0) or 0

    factors = []
    total_score = 0
    bullish_factors = []
    risk_factors = []

    for key, score in factor_scores.items():
        strat = strategies.get(key, {})
        max_score = strat.get('max_score', 20)
        strat_name = strat.get('name', key)
        strat_logic = strat.get('logic', '')

        # 计算置信度
        ratio = score / max_score if max_score > 0 else 0
        if ratio >= 0.7:
            confidence = 'high'
        elif ratio >= 0.4:
            confidence = 'medium'
        else:
            confidence = 'low'

        # 生成预测描述
        prediction = _generate_factor_prediction(key, stock, score, max_score, strat)

        factor_entry = {
            'key': key,
            'name': strat_name,
            'score': score,
            'max_score': max_score,
            'prediction': prediction,
            'confidence': confidence,
            'predicted_up': score >= max_score * 0.4  # 得分超过40%认为预测上涨
        }
        factors.append(factor_entry)
        total_score += score

        if confidence in ('high', 'medium') and score > 0:
            bullish_factors.append(strat_name)

    # 风险因子识别
    if turnover > 25:
        risk_factors.append(f'换手率{turnover:.1f}%偏高，可能存在短期见顶风险')
    if change_pct >= 9.9:
        risk_factors.append('已涨停，次日可能面临获利盘抛压')
    if not concept_tags:
        risk_factors.append('无概念标签，缺乏板块共振支撑')

    # 找出得分最高的因子作为核心论点
    top_factors = sorted(factors, key=lambda x: x['score'], reverse=True)[:2]
    key_thesis_parts = []
    for f in top_factors:
        if f['score'] > 0:
            key_thesis_parts.append(f['prediction'])
    key_thesis = '；'.join(key_thesis_parts) if key_thesis_parts else '无明显看多因子'

    # 综合预测
    if total_score >= 80:
        overall = f'综合评分{total_score}分，{"、".join(bullish_factors[:3])}等多重利好共振，预测短期内继续上涨概率较高'
    elif total_score >= 60:
        overall = f'综合评分{total_score}分，有一定利好因素，但需注意风险'
    elif total_score >= 40:
        overall = f'综合评分{total_score}分，利好因素不足，建议观望'
    else:
        overall = f'综合评分{total_score}分，缺乏明显利好，不建议参与'

    return {
        'code': code,
        'name': name,
        'change_pct': change_pct,
        'turnover': turnover,
        'concept_tags': concept_tags,
        'pre_attribution': {
            'total_score': total_score,
            'factors': factors,
            'overall_prediction': overall,
            'risk_factors': risk_factors,
            'key_thesis': key_thesis,
        }
    }


def _generate_factor_prediction(key, stock, score, max_score, strat):
    """为每个因子生成自然语言预测"""
    name = stock.get('name', '')
    change_pct = stock.get('change_pct', 0) or 0
    turnover = stock.get('turnover', 0) or 0
    concept_tags = stock.get('concept_tags', [])

    if key == 'hot_sector_boost' and score > 0:
        # 找到匹配的板块
        return f'{name}所属概念板块涨幅靠前，板块热度传导预计推动个股上涨'
    elif key == 'hot_rank' and score > 0:
        rank = stock.get('rank', 999)
        return f'热榜排名第{rank}名，市场关注度{"极高" if rank <= 3 else "较高" if rank <= 10 else "中等"}，资金关注度持续'
    elif key == 'momentum' and score > 0:
        if change_pct >= 9.9:
            return f'涨停封板(涨幅{change_pct:.2f}%)，买盘力量极强，动能充沛'
        elif change_pct >= 5:
            return f'涨幅{change_pct:.2f}%，资金推动力度较强'
        else:
            return f'涨幅{change_pct:.2f}%，资金有一定推动'
    elif key == 'skyrocket' and score > 0:
        return f'上榜飙升榜，关注度急速上升，新增资金正在关注'
    elif key == 'news_heat' and score > 0:
        return f'新闻热词匹配{name}相关概念，事件驱动型上涨'
    elif key == 'turnover' and score > 0:
        return f'换手率{turnover:.1f}%，交投{"活跃适中" if 5 <= turnover <= 15 else "较活跃"}'
    elif key == 'concept_richness' and score > 0:
        return f'拥有{len(concept_tags)}个概念标签，板块轮动中更容易受益'
    else:
        return f'{strat.get("name", key)}得分{score}/{max_score}'


def post_attribution(pre_attr_result, current_change_pct):
    """
    事后归因：对比事前预测和实际结果

    参数:
        pre_attr_result: 事前归因结果
        current_change_pct: 当前涨跌幅（用于对比）

    返回:
        {
            'code': '002281',
            'name': '光迅科技',
            'pre_change_pct': 10.0,
            'post_change_pct': 5.2,
            'delta': -4.8,
            'verdict': 'partial_hit',  # hit / miss / partial_hit
            'factor_analysis': [
                {
                    'key': 'hot_sector_boost',
                    'name': '热门板块加成',
                    'pre_score': 25,
                    'predicted_up': True,
                    'actual_up': True,
                    'correct': True,
                    'analysis': '板块确实继续走强，预测正确'
                },
                ...
            ],
            'lessons': [
                '热门板块加成因子预测正确，CPO板块后续继续上涨',
                '涨跌动量因子预测部分正确，涨停后次日高开低走'
            ],
            'optimization': [
                '涨停次日应降低动量因子权重，考虑获利盘抛压'
            ]
        }
    """
    code = pre_attr_result.get('code', '')
    name = pre_attr_result.get('name', '')
    pre_change = pre_attr_result.get('change_pct', 0) or 0
    pre_attr = pre_attr_result.get('pre_attribution', {})
    factors = pre_attr.get('factors', [])

    delta = round(current_change_pct - pre_change, 2)
    actual_up = current_change_pct > 0

    # 判定结果
    if delta > 2:
        verdict = 'hit'
    elif delta < -2:
        verdict = 'miss'
    else:
        verdict = 'partial_hit'

    # 逐因子分析
    factor_analysis = []
    lessons = []
    optimizations = []

    for f in factors:
        key = f['key']
        predicted_up = f.get('predicted_up', False)
        correct = (predicted_up and actual_up) or (not predicted_up and not actual_up)

        analysis = _analyze_factor_result(key, f, actual_up, delta, current_change_pct)

        factor_analysis.append({
            'key': key,
            'name': f['name'],
            'pre_score': f['score'],
            'predicted_up': predicted_up,
            'actual_up': actual_up,
            'correct': correct,
            'analysis': analysis,
        })

        if correct:
            lessons.append(f'{f["name"]}预测正确：{analysis}')
        else:
            lessons.append(f'{f["name"]}预测错误：{analysis}')
            opt = _generate_optimization(key, f, delta)
            if opt:
                optimizations.append(opt)

    return {
        'code': code,
        'name': name,
        'pre_change_pct': pre_change,
        'post_change_pct': current_change_pct,
        'delta': delta,
        'verdict': verdict,
        'verdict_label': {'hit': '命中', 'miss': '未命中', 'partial_hit': '部分命中'}[verdict],
        'factor_analysis': factor_analysis,
        'lessons': lessons,
        'optimizations': optimizations,
    }


def _analyze_factor_result(key, factor, actual_up, delta, current_change_pct):
    """分析单个因子的预测结果"""
    score = factor['score']
    confidence = factor.get('confidence', 'low')

    if key == 'hot_sector_boost':
        if actual_up:
            return '板块热度确实传导到个股，板块共振逻辑有效'
        else:
            return '板块虽热但个股未跟随，可能个股已提前透支涨幅'
    elif key == 'hot_rank':
        if actual_up:
            return '高关注度确实带来资金流入'
        else:
            return '高关注度未转化为上涨，可能为短期炒作'
    elif key == 'momentum':
        if delta > 0:
            return '动量延续，资金推动持续有效'
        elif delta < -5:
            return '动量反转，涨停/大涨后获利盘出逃'
        else:
            return '动量减弱，涨势趋缓'
    elif key == 'skyrocket':
        if actual_up:
            return '关注度上升确实带来增量资金'
        else:
            return '飙升关注后资金未持续跟进'
    elif key == 'news_heat':
        if actual_up:
            return '新闻事件驱动有效，市场认可该利好'
        else:
            return '新闻利好已提前消化或市场不认可'
    elif key == 'turnover':
        if actual_up:
            return '换手率适中，交投活跃支撑上涨'
        else:
            return '换手率过高导致抛压增大'
    elif key == 'concept_richness':
        if actual_up:
            return '多概念标签带来板块轮动受益'
        else:
            return '概念虽多但无领涨概念，效果有限'
    return '因子表现待进一步观察'


def _generate_optimization(key, factor, delta):
    """根据错误预测生成优化建议"""
    if key == 'momentum' and delta < -3:
        return '涨停/大涨次日动量因子权重应降低，需考虑获利盘抛压效应'
    elif key == 'hot_sector_boost' and delta < 0:
        return '板块涨幅大但个股不涨时，需检查个股是否已提前上涨（透支）'
    elif key == 'news_heat' and delta < 0:
        return '新闻热度因子需区分利好类型，短期题材炒作持续性差'
    elif key == 'turnover' and delta < -3:
        return '换手率过高(>25%)时应增加风险扣分'
    elif key == 'skyrocket' and delta < 0:
        return '飙升榜上榜后次日回落概率较高，需结合其他因子综合判断'
    return None


def batch_post_attribution(recommendation, current_data):
    """
    批量事后归因：对一批推荐进行事后归因
    """
    from .strategy_engine import update_strategy_weights

    if not recommendation or not current_data:
        return None

    rec_list = recommendation.get('recommendations', [])
    current_stocks = {s['code']: s for s in current_data.get('data', [])} if current_data else {}

    results = []
    feedback = {}  # 用于策略进化

    for rec in rec_list:
        code = rec.get('code', '')
        curr = current_stocks.get(code, {})
        curr_change = curr.get('change_pct', 0) or 0

        # 事后归因
        post_result = post_attribution(rec, curr_change)
        results.append(post_result)

        # 收集因子反馈
        pre_attr = rec.get('pre_attribution', {})
        for f in pre_attr.get('factors', []):
            key = f.get('key', '')
            if key and key not in feedback:
                feedback[key] = {
                    'predicted_up': f.get('predicted_up', False),
                    'actual_up': curr_change > 0,
                    'delta': post_result.get('delta', 0),
                }

    # 统计
    hits = sum(1 for r in results if r['verdict'] == 'hit')
    partial = sum(1 for r in results if r['verdict'] == 'partial_hit')
    misses = sum(1 for r in results if r['verdict'] == 'miss')
    total = len(results)

    # 策略进化
    evolution = update_strategy_weights(feedback)

    # 收集所有优化建议
    all_optimizations = []
    for r in results:
        for opt in r.get('optimizations', []):
            if opt not in all_optimizations:
                all_optimizations.append(opt)

    # 收集所有经验教训
    all_lessons = []
    for r in results:
        for lesson in r.get('lessons', []):
            all_lessons.append({
                'stock': r['name'],
                'verdict': r['verdict_label'],
                'lesson': lesson,
            })

    return {
        'backtest_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'recommendation_time': recommendation.get('generate_time', ''),
        'summary': {
            'total': total,
            'hits': hits,
            'partial_hits': partial,
            'misses': misses,
            'hit_rate': round((hits + partial * 0.5) / total * 100, 1) if total else 0,
            'win_rate': round(hits / total * 100, 1) if total else 0,
            'avg_delta': round(sum(r['delta'] for r in results) / total, 2) if total else 0,
        },
        'results': results,
        'lessons': all_lessons,
        'optimizations': all_optimizations,
        'evolution': evolution,
    }


def save_attribution(result):
    """保存归因结果"""
    history = load_attributions()
    history.insert(0, result)
    history = history[:50]  # 保留50条

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ATTRIBUTION_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_attributions():
    """加载归因历史"""
    try:
        with open(ATTRIBUTION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []
