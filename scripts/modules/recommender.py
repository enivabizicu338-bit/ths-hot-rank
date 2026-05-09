#!/usr/bin/env python3
"""
智能选股推荐引擎 - 多维度评分系统
"""
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
RECOMMEND_FILE = os.path.join(DATA_DIR, 'recommendations.json')


def _load_json(filename):
    """加载JSON文件"""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f'[recommender] 加载 {filename} 失败: {e}')
        return None


def _score_hot_rank(rank):
    """热榜排名分 (0-25)"""
    if rank <= 3:
        return 25
    elif rank <= 10:
        return 20
    elif rank <= 30:
        return 15
    elif rank <= 50:
        return 10
    elif rank <= 100:
        return 5
    return 0


def _score_skyrocket(rank):
    """飙升榜分 (0-25)"""
    if rank <= 5:
        return 25
    elif rank <= 15:
        return 20
    elif rank <= 30:
        return 15
    else:
        return 8


def _score_momentum(change_pct):
    """涨跌幅动量 (0-20)"""
    if change_pct >= 9.9:
        return 20
    elif change_pct >= 7:
        return 18
    elif change_pct >= 5:
        return 15
    elif change_pct >= 3:
        return 10
    elif change_pct >= 0:
        return 5
    return 0


def _score_turnover(turnover):
    """换手率分 (0-10)"""
    if 5 <= turnover <= 15:
        return 10
    elif 15 < turnover <= 25:
        return 8
    elif 3 <= turnover < 5:
        return 6
    elif turnover > 25:
        return 4
    return 0


def _score_sector(stock, sectors):
    """板块共振分 (0-15)"""
    if not sectors or not stock.get('concept_tags'):
        return 0, '无板块数据'

    concept_tags = stock.get('concept_tags', [])
    best_score = 0
    best_reason = ''

    for sector in sectors:
        sector_name = sector.get('\u677f\u5757\u540d\u79f0', '')
        sector_change = sector.get('\u6da8\u8dcc\u5e45', 0) or 0

        matched = False
        for tag in concept_tags:
            if tag and sector_name and (tag in sector_name or sector_name in tag):
                matched = True
                break

        if matched:
            if sector_change >= 3:
                score = 15
            elif sector_change >= 2:
                score = 12
            elif sector_change >= 1:
                score = 8
            elif sector_change > 0:
                score = 5
            else:
                score = 0

            if score > best_score:
                best_score = score
                best_reason = f'所属板块[{sector_name}]涨幅{sector_change:.2f}%'

    if best_score == 0:
        return 0, '所属板块表现平淡'
    return best_score, best_reason


def _score_news(stock, keywords):
    """新闻热度分 (0-15)"""
    if not keywords:
        return 0, '暂无新闻关键词数据'

    stock_name = stock.get('name', '')
    concept_tags = stock.get('concept_tags', [])
    match_count = 0
    matched_words = []

    for kw in keywords:
        kw_name = kw.get('name', '')
        if not kw_name:
            continue
        if stock_name and kw_name in stock_name:
            match_count += 1
            matched_words.append(kw_name)
            continue
        for tag in concept_tags:
            if tag and kw_name and (kw_name in tag or tag in kw_name):
                match_count += 1
                if kw_name not in matched_words:
                    matched_words.append(kw_name)
                break

    if match_count >= 3:
        score = 15
    elif match_count >= 2:
        score = 12
    elif match_count >= 1:
        score = 8
    else:
        score = 0

    if score > 0:
        reason = '新闻热词匹配: ' + ', '.join(matched_words[:3])
    else:
        reason = '未匹配到新闻热词'

    return score, reason


def _score_concepts(stock):
    """概念丰富度 (0-5)"""
    concept_tags = stock.get('concept_tags', [])
    count = len(concept_tags)

    if count >= 3:
        score = 5
    elif count >= 2:
        score = 3
    else:
        score = 1

    reason = f'拥有{count}个概念标签'
    return score, reason


def score_stock(stock, hot_list, skyrocket_list, sectors, keywords):
    """
    对单只股票多维度打分
    返回包含code, name, total_score, scores, reasons等字段的字典
    """
    code = stock.get('code', '')
    name = stock.get('name', '')
    change_pct = stock.get('change_pct', 0) or 0
    turnover = stock.get('turnover', 0) or 0
    hot_rank = stock.get('rank', 999)
    hot_value = stock.get('hot_value', '0')
    concept_tags = stock.get('concept_tags', [])

    scores = {}
    reasons = []

    # 1. 热榜排名分
    hot_score = _score_hot_rank(hot_rank)
    scores['hot_rank'] = hot_score
    if hot_score > 0:
        reasons.append(f'热榜排名第{hot_rank}名，得{hot_score}分')

    # 2. 飙升榜分
    skyrocket_rank = None
    skyrocket_score = 0
    if skyrocket_list:
        for sk in skyrocket_list:
            if sk.get('code') == code:
                skyrocket_rank = sk.get('rank')
                skyrocket_score = _score_skyrocket(skyrocket_rank)
                break
    scores['skyrocket'] = skyrocket_score
    if skyrocket_score > 0:
        reasons.append(f'飙升榜排名第{skyrocket_rank}名，得{skyrocket_score}分')

    # 3. 涨跌幅动量
    momentum_score = _score_momentum(change_pct)
    scores['momentum'] = momentum_score
    if momentum_score >= 20:
        reasons.append(f'涨停(涨幅{change_pct:.2f}%)，动量得分{momentum_score}')
    elif momentum_score >= 15:
        reasons.append(f'涨幅{change_pct:.2f}%，动量强劲得{momentum_score}分')
    elif momentum_score >= 10:
        reasons.append(f'涨幅{change_pct:.2f}%，动量良好得{momentum_score}分')
    elif momentum_score > 0:
        reasons.append(f'涨幅{change_pct:.2f}%，动量一般得{momentum_score}分')

    # 4. 换手率
    turnover_score = _score_turnover(turnover)
    scores['turnover'] = turnover_score
    if turnover_score >= 8:
        reasons.append(f'换手率{turnover:.1f}%，交投活跃得{turnover_score}分')
    elif turnover_score > 0:
        reasons.append(f'换手率{turnover:.1f}%，得{turnover_score}分')

    # 5. 板块共振
    sector_score, sector_reason = _score_sector(stock, sectors)
    scores['sector'] = sector_score
    if sector_score > 0:
        reasons.append(sector_reason)

    # 6. 新闻热度
    news_score, news_reason = _score_news(stock, keywords)
    scores['news'] = news_score
    if news_score > 0:
        reasons.append(news_reason)

    # 7. 概念丰富度
    concept_score, concept_reason = _score_concepts(stock)
    scores['concepts'] = concept_score
    if concept_score >= 3:
        reasons.append(concept_reason)

    total_score = sum(scores.values())

    return {
        'code': code,
        'name': name,
        'total_score': total_score,
        'scores': scores,
        'reasons': reasons,
        'change_pct': change_pct,
        'turnover': turnover,
        'hot_rank': hot_rank,
        'hot_value': hot_value,
        'skyrocket_rank': skyrocket_rank,
        'concept_tags': concept_tags,
    }


def generate_recommendations(min_count=5):
    """
    生成推荐列表
    """
    hot_data = _load_json('current.json')
    skyrocket_data = _load_json('skyrocket.json')
    sectors_data = _load_json('sectors.json')
    keywords_data = _load_json('keywords.json')

    if not hot_data or not hot_data.get('data'):
        print('[recommender] 无热榜数据')
        return None

    hot_list = hot_data.get('data', [])
    skyrocket_list = skyrocket_data.get('data', []) if skyrocket_data else []
    sectors = sectors_data.get('data', []) if sectors_data else []
    keywords = keywords_data.get('data', []) if keywords_data else []

    candidates = hot_list[:100]
    scored = []
    for stock in candidates:
        result = score_stock(stock, hot_list, skyrocket_list, sectors, keywords)
        scored.append(result)

    scored.sort(key=lambda x: x['total_score'], reverse=True)

    rec_count = max(min_count, 8)
    recommendations = scored[:rec_count]

    total_analyzed = len(scored)
    avg_score = sum(r['total_score'] for r in recommendations) / len(recommendations) if recommendations else 0

    result = {
        'generate_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source_update_time': hot_data.get('update_time', ''),
        'stats': {
            'total_analyzed': total_analyzed,
            'recommended': len(recommendations),
            'avg_score': round(avg_score, 1),
            'max_score': recommendations[0]['total_score'] if recommendations else 0,
            'min_score': recommendations[-1]['total_score'] if recommendations else 0,
        },
        'recommendations': recommendations,
    }

    _save_to_history(result)

    print(f'[recommender] 生成推荐{len(recommendations)}只，最高分{result["stats"]["max_score"]}')
    return result


def _save_to_history(result):
    """保存推荐结果到历史记录（最多100条）"""
    history = load_history()
    history.insert(0, result)
    history = history[:100]

    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(RECOMMEND_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'[recommender] 保存历史记录失败: {e}')


def load_history():
    """加载历史推荐"""
    try:
        with open(RECOMMEND_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def backtest_recommendation(recommendation, current_data):
    """
    回测：对比推荐时涨幅和当前涨幅
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
