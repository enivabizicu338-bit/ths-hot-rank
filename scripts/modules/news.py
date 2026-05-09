#!/usr/bin/env python3
"""
A股新闻获取 - 东方财富数据源
"""
import json
import re
import time
import requests

EM_NEWS_URL = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"

def fetch_news(page_index=1, page_size=30):
    try:
        params = {
            "client": "web",
            "biz": "web_news_col",
            "column": "353",
            "order": "1",
            "needInteractData": "0",
            "page_index": str(page_index),
            "page_size": str(page_size),
            "fields": "code,showTime,title,mediaName,summary,image,url,uniqueUrl,Np_dst",
            "types": "1,20",
            "req_trace": str(int(time.time() * 1000)),
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://finance.eastmoney.com/",
        }
        response = requests.get(EM_NEWS_URL, params=params, headers=headers, timeout=15)
        text = response.text
        text = re.sub(r'^jQuery\d+_\d+\(', '', text)
        text = re.sub(r'\)$', '', text)
        data = json.loads(text)

        news_list = data.get("data", {}).get("list", [])
        result = []
        for item in news_list:
            result.append({
                "title": item.get("title", ""),
                "summary": item.get("summary", ""),
                "showTime": item.get("showTime", ""),
                "mediaName": item.get("mediaName", ""),
                "url": item.get("url", ""),
                "image": item.get("image", ""),
            })
        print(f"[新闻] 获取 {len(result)} 条")
        return result
    except Exception as e:
        print(f"[新闻] 获取失败: {e}")
        return []