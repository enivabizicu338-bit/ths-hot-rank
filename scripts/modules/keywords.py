#!/usr/bin/env python3
"""
新闻关键词提取 - 匹配板块、概念、股票名称
"""
import json
import re
import time
import os
from collections import Counter

try:
    import jieba
    import jieba.analyse
except ImportError:
    jieba = None

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

# 金融领域停用词
STOP_WORDS = set([
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
    '自己', '这', '他', '她', '它', '们', '那', '些', '什么', '如何', '怎么', '哪',
    '为什么', '可以', '能', '这个', '那个', '这些', '那些', '但是', '而且', '或者',
    '因为', '所以', '如果', '虽然', '但是', '已经', '正在', '将', '被', '把',
    '对', '与', '及', '等', '中', '为', '从', '以', '其', '之', '或', '但',
    '比', '更', '最', '将', '该', '此', '每', '各', '约', '达', '超', '余',
    '元', '亿', '万', '亿', '美元', '亿元', '万元', '万股', '同比', '环比',
    '今日', '昨日', '本周', '本月', '今年', '去年', '同比', '环比',
    '记者', '表示', '认为', '指出', '透露', '介绍', '称', '据',
    '公司', '市场', '投资者', '机构', '分析师', '行业', '板块', '概念',
    '涨停', '跌停', '涨幅', '跌幅', '涨幅达', '收涨', '收跌',
    '报', '收于', '开盘', '收盘', '盘中', '尾盘', '早盘', '午盘',
    '发布', '公告', '披露', '显示', '数据', '消息', '新闻', '资讯',
    '第一', '第二', '第三', '首次', '目前', '当前', '近期', '近日',
    '方面', '期间', '以来', '左右', '以上', '以下', '之间',
    '大增', '大涨', '大跌', '暴涨', '暴跌', '飙升', '回落', '反弹',
    '值得关注', '引发关注', '备受关注', '引发市场', '市场关注',
])

def load_stock_names():
    """从当前热榜数据加载股票名称"""
    names = set()
    try:
        filepath = os.path.join(DATA_DIR, 'current.json')
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for stock in data.get('data', []):
            name = stock.get('name', '')
            if name:
                names.add(name)
            for tag in stock.get('concept_tags', []):
                if tag:
                    names.add(tag)
    except:
        pass
    
    # 加载板块名称
    try:
        filepath = os.path.join(DATA_DIR, 'sectors.json')
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for sector in data.get('data', []):
            name = sector.get('\u677f\u5757\u540d\u79f0', '')
            if name:
                names.add(name)
    except:
        pass
    
    return names

def extract_keywords(news_list):
    """
    从新闻列表中提取关键词，匹配板块/概念/股票
    返回: [{name, value, category}, ...]
    """
    if not news_list:
        return []
    
    # 加载已知实体名称
    entity_names = load_stock_names()
    
    # 合并所有新闻文本
    all_text = []
    for news in news_list:
        title = news.get('title', '')
        summary = news.get('summary', '')
        all_text.append(title + ' ' + summary)
    
    combined_text = ' '.join(all_text)
    
    # 1. 直接匹配已知实体（股票名、板块名、概念名）
    entity_counter = Counter()
    for name in entity_names:
        count = combined_text.count(name)
        if count > 0:
            entity_counter[name] = count
    
    # 2. jieba分词提取关键词
    word_counter = Counter()
    if jieba:
        for text in all_text:
            # 使用jieba的TF-IDF提取关键词
            words = jieba.analyse.extract_tags(text, topK=50, withWeight=True)
            for word, weight in words:
                if word not in STOP_WORDS and len(word) >= 2:
                    word_counter[word] += weight
    else:
        # 无jieba时用简单正则
        for text in all_text:
            # 提取2-4字中文词组
            words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
            for w in words:
                if w not in STOP_WORDS:
                    word_counter[w] += 1
    
    # 3. 合并结果，实体词权重加倍
    final_counter = Counter()
    for word, count in word_counter.items():
        if word in entity_names:
            final_counter[word] = count * 3  # 实体词加权
        else:
            final_counter[word] = count
    
    for word, count in entity_counter.items():
        final_counter[word] = final_counter.get(word, 0) + count * 5  # 直接匹配加权更高
    
    # 4. 过滤停用词和短词
    result = []
    for word, value in final_counter.most_common(100):
        if word in STOP_WORDS or len(word) < 2:
            continue
        # 判断类别
        if word in entity_names:
            category = 'entity'
        elif re.match(r'^[\u4e00-\u9fff]+$', word):
            category = 'keyword'
        else:
            category = 'other'
        
        result.append({
            'name': word,
            'value': round(value, 1),
            'category': category
        })
    
    # 按value排序，取前80个
    result.sort(key=lambda x: x['value'], reverse=True)
    return result[:80]


if __name__ == '__main__':
    # 测试
    test_news = [
        {'title': '机器人概念股全线爆发 减速器龙头涨停', 'summary': '机器人执行器板块大涨，巨轮智能等多股涨停'},
        {'title': '光纤概念持续走强 光迅科技两连板', 'summary': '共封装光学CPO概念活跃，通鼎互联涨停'},
    ]
    keywords = extract_keywords(test_news)
    for k in keywords[:10]:
        print(f"{k['name']}: {k['value']} ({k['category']})")