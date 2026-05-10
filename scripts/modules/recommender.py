#!/usr/bin/env python3
"""
智能选股推荐引擎 v2 - 集成策略引擎 + 事前归因
"""
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
RECOMMEND_FILE = os.path.join(DATA_DIR, 'recommendations.json')


def _load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f'[recommender] 加载 {filename} 失败: {e}')
        return None


def _calc_hot_sector_boost(stock, sectors, strategies):
    """热门板块加成 (使用策略权重)"""
    concept_tags = stock.get('concept_tags', [])
    if not concept_tags or not sectors:
        return 0

    strat = strategies.get('hot_sector_boost', {})
    max_score = strat.get('max_score', 30)

    best_score = 0
    best_sector_name = ''
    best_sector_change = 0
    best_sector_rank = 999

    for i, sector in enumerate(sectors):
        sector_name = sector.get('\u677f\u5757\u540d\u79f0', '')
        sector_change = sector.get('\u6da8\u8dcc\u5e45', 0) or 0

        for tag in concept_tags:
            if tag and sector_name and (tag in sector_name or sector_name in tag):
                # 计算得分
                if sector_change >= 4:
                    score = 25
                elif sector_change >= 3:
                    score = 22
                elif sector_change >= 2:
                    score = 18
                elif sector_change >= 1:
                    score = 12
                elif sector_change > 0:
                    score = 6
                else:
                    score = 0

                # 板块排名加成（前10名额外加分）
                if i < 10 and score > 0:
                    score = min(score + 5, max_score)

                if score > best_score:
                    best_score = score
                    best_sector_name = sector_name
                    best_sector_change = sector_change
                    best_sector_rank = i + 1
                break

    return best_score


def _calc_hot_rank(stock, strategies):
    """热榜排名"""
    rank = stock.get('rank', 999)
    strat = strategies.get('hot_rank', {})
    max_score = strat.get('max_score', 20)

    if rank <= 3: return max_score
    elif rank <= 10: return int(max_score * 0.8)
    elif rank <= 20: return int(max_score * 0.6)
    elif rank <= 50: return int(max_score * 0.4)
    elif rank <= 100: return int(max_score * 0.2)
    return 0


def _calc_momentum(stock, strategies):
    """涨跌动量"""
    change_pct = stock.get('change_pct', 0) or 0
    strat = strategies.get('momentum', {})
    max_score = strat.get('max_score', 20)

    if change_pct >= 9.9: return max_score
    elif change_pct >= 7: return int(max_score * 0.85)
    elif change_pct >= 5: return int(max_score * 0.7)
    elif change_pct >= 3: return int(max_score * 0.5)
    elif change_pct >= 0: return int(max_score * 0.2)
    return 0


def _calc_skyrocket(stock, skyrocket_list, strategies):
    """飙升榜"""
    code = stock.get('code', '')
    strat = strategies.get('skyrocket', {})
    max_score = strat.get('max_score', 15)

    if not skyrocket_list:
        return 0
    for sk in skyrocket_list:
        if sk.get('code') == code:
            rank = sk.get('rank', 999)
            if rank <= 5: return max_score
            elif rank <= 15: return int(max_score * 0.8)
            elif rank <= 30: return int(max_score * 0.6)
            else: return int(max_score * 0.3)
    return 0


def _calc_news_heat(stock, keywords, strategies):
    """新闻热度"""
    stock_name = stock.get('name', '')
    concept_tags = stock.get('concept_tags', [])
    strat = strategies.get('news_heat', {})
    max_score = strat.get('max_score', 15)

    if not keywords:
        return 0

    match_count = 0
    for kw in keywords:
        kw_name = kw.get('name', '')
        if not kw_name: continue
        if stock_name and kw_name in stock_name:
            match_count += 1; continue
        for tag in concept_tags:
            if tag and kw_name and (kw_name in tag or tag in kw_name):
                match_count += 1; break

    if match_count >= 3: return max_score
    elif match_count >= 2: return int(max_score * 0.75)
    elif match_count >= 1: return int(max_score * 0.5)
    return 0


def _calc_turnover(stock, strategies):
    """换手率"""
    turnover = stock.get('turnover', 0) or 0
    strat = strategies.get('turnover', {})
    max_score = strat.get('max_score', 10)

    if 5 <= turnover <= 15: return max_score
    elif 15 < turnover <= 25: return int(max_score * 0.7)
    elif 3 <= turnover < 5: return int(max_score * 0.5)
    elif turnover > 25: return int(max_score * 0.3)
    elif turnover > 0: return int(max_score * 0.1)
    return 0


def _calc_concept_richness(stock, strategies):
    """概念丰富度"""
    concept_tags = stock.get('concept_tags', [])
    count = len(concept_tags)
    strat = strategies.get('concept_richness', {})
    max_score = strat.get('max_score', 5)

    if count >= 4: return max_score
    elif count >= 3: return int(max_score * 0.8)
    elif count >= 2: return int(max_score * 0.6)
    elif count >= 1: return int(max_score * 0.2)
    return 0


def score_stock_v2(stock, hot_list, skyrocket_list, sectors, keywords, strategies):
    """v2评分：使用策略引擎权重 + 事前归因"""
    from .attribution import pre_attribution

    factor_scores = {
        'hot_sector_boost': _calc_hot_sector_boost(stock, sectors, strategies),
        'hot_rank': _calc_hot_rank(stock, strategies),
        'momentum': _calc_momentum(stock, strategies),
        'skyrocket': _calc_skyrocket(stock, skyrocket_list, strategies),
        'news_heat': _calc_news_heat(stock, keywords, strategies),
        'turnover': _calc_turnover(stock, strategies),
        'concept_richness': _calc_concept_richness(stock, strategies),
    }

    total_score = sum(factor_scores.values())

    # 事前归因
    attr = pre_attribution(stock, factor_scores, strategies)

    return {
        'code': stock.get('code', ''),
        'name': stock.get('name', ''),
        'total_score': total_score,
        'scores': factor_scores,
        'change_pct': stock.get('change_pct', 0) or 0,
        'turnover': stock.get('turnover', 0) or 0,
        'hot_rank': stock.get('rank', 999),
        'hot_value': stock.get('hot_value', '0'),
        'skyrocket_rank': None,
        'concept_tags': stock.get('concept_tags', []),
        'pre_attribution': attr.get('pre_attribution', {}),
    }


def generate_recommendations(min_count=5):
    """生成推荐（v2：集成策略引擎+事前归因）"""
    from .strategy_engine import load_strategies

    hot_data = _load_json('current.json')
    skyrocket_data = _load_json('skyrocket.json')
    sectors_data = _load_json('sectors.json')
    keywords_data = _load_json('keywords.json')

    if not hot_data or not hot_data.get('data'):
        return None

    strategies = load_strategies()
    hot_list = hot_data.get('data', [])
    skyrocket_list = skyrocket_data.get('data', []) if skyrocket_data else []
    sectors = sectors_data.get('data', []) if sectors_data else []
    keywords = keywords_data.get('data', []) if keywords_data else []

    # 设置飙升排名
    scored = []
    for stock in hot_list[:100]:
        result = score_stock_v2(stock, hot_list, skyrocket_list, sectors, keywords, strategies)
        # 查找飙升排名
        for sk in skyrocket_list:
            if sk.get('code') == result['code']:
                result['skyrocket_rank'] = sk.get('rank')
                break
        scored.append(result)

    scored.sort(key=lambda x: x['total_score'], reverse=True)
    rec_count = max(min_count, 8)
    recommendations = scored[:rec_count]

    avg_score = sum(r['total_score'] for r in recommendations) / len(recommendations) if recommendations else 0

    result = {
        'generate_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source_update_time': hot_data.get('update_time', ''),
        'version': 'v2',
        'stats': {
            'total_analyzed': len(scored),
            'recommended': len(recommendations),
            'avg_score': round(avg_score, 1),
            'max_score': recommendations[0]['total_score'] if recommendations else 0,
        },
        'recommendations': recommendations,
    }

    _save_to_history(result)
    print(f'[recommender v2] 推荐{len(recommendations)}只，最高分{result["stats"]["max_score"]}')
    return result


def _save_to_history(result):
    history = load_history()
    history.insert(0, result)
    history = history[:100]
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(RECOMMEND_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'[recommender] 保存失败: {e}')


def load_history():
    try:
        with open(RECOMMEND_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def backtest_recommendation(recommendation, current_data):
    """
    回测：对比推荐时涨幅和当前涨幅（兼容旧版v1推荐）
    """
    if not recommendation or not current_data or not current_data.get('data'):
        return {'error': '数据不足'}

    current_stocks = {s['code']: s for s in current_data.get('data', [])}
    rec_list = recommendation.get('recommendations', [])

    results = []
    hits = 0

    for rec in rec_list:
        code = rec.get('code', '')
        name = rec.get('name', '')
        orig_change = rec.get('change_pct', 0) or 0

        curr = current_stocks.get(code, {})
        curr_change = curr.get('change_pct', 0) or 0

        delta = round(curr_change - orig_change, 2)
        hit = delta >= 0
        if hit:
            hits += 1

        results.append({
            'code': code,
            'name': name,
            'original_change_pct': orig_change,
            'current_change_pct': curr_change,
            'delta': delta,
            'hit': hit,
        })

    total = len(results)
    win_rate = round(hits / total * 100, 1) if total > 0 else 0
    avg_delta = round(sum(r['delta'] for r in results) / total, 2) if total > 0 else 0

    return {
        'backtest_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'recommendation_time': recommendation.get('generate_time', ''),
        'win_rate': win_rate,
        'avg_delta': avg_delta,
        'hits': hits,
        'total': total,
        'results': results,
    }


if __name__ == '__main__':
    rec = generate_recommendations()
    if rec:
        print(f'推荐{rec["stats"]["recommended"]}只，平均分{rec["stats"]["avg_score"]}')
        for r in rec['recommendations'][:5]:
            print(f'  {r["name"]}({r["code"]}): {r["total_score"]}分')
    else:
        print('生成推荐失败')
