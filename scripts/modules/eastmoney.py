#!/usr/bin/env python3
"""
东方财富数据获取模块
获取今日浏览排名、换手率、实时价格、涨跌幅
"""
import requests
import json

def fetch_eastmoney_data(stock_codes):
    """
    获取东方财富热榜数据
    返回: {code: {browse_rank, price, change_pct, turnover}}
    """
    result = {}
    
    try:
        # 东财热榜API - 获取前100只热门股票
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 100,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f12",
            "fs": "m:0+t:6,m:0+t:13,m:1+t:2,m:1+t:23",
            "fields": "f12,f13,f14,f2,f3,f5,f8,f10,f20,f21,f22,f33,f34,f35,f36,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91,f92,f93,f94,f95,f96,f97,f98,f99,f100"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://guba.eastmoney.com/"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if data and data.get("data") and data["data"].get("diff"):
            for idx, item in enumerate(data["data"]["diff"]):
                code = item.get("f12", "")
                if code:
                    # f2=最新价, f3=涨跌幅, f8=换手率, f20=总市值, f21=流通市值
                    price = item.get("f2", 0)
                    change_pct = item.get("f3", 0)
                    turnover = item.get("f8", 0)
                    
                    # 处理价格数据
                    if price and price != "-":
                        try:
                            price = float(price)
                        except:
                            price = 0
                    else:
                        price = 0
                    
                    # 处理涨跌幅
                    if change_pct and change_pct != "-":
                        try:
                            change_pct = float(change_pct)
                        except:
                            change_pct = 0
                    else:
                        change_pct = 0
                    
                    # 处理换手率
                    if turnover and turnover != "-":
                        try:
                            turnover = float(turnover)
                        except:
                            turnover = 0
                    else:
                        turnover = 0
                    
                    result[code] = {
                        "browse_rank": idx + 1,  # 浏览排名
                        "price": price,
                        "change_pct": change_pct,
                        "turnover": turnover
                    }
        
        print(f"[东财] 成功获取 {len(result)} 只股票数据")
        
    except Exception as e:
        print(f"[东财] 获取数据失败: {e}")
    
    return result


def fetch_eastmoney_hot_list():
    """
    获取东方财富热榜排名（备用方法）
    """
    result = {}
    
    try:
        # 东财热榜API
        url = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYBJListV2"
        params = {
            "code": "SH000001",
            "type": "3"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://emweb.securities.eastmoney.com/"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if data and data.get("result"):
            for idx, item in enumerate(data["result"].get("data", [])):
                code = item.get("SECURITY_CODE", "")
                if code:
                    result[code] = {
                        "browse_rank": idx + 1,
                        "name": item.get("SECURITY_NAME_ABBR", "")
                    }
        
    except Exception as e:
        print(f"[东财热榜] 获取失败: {e}")
    
    return result


if __name__ == "__main__":
    # 测试
    data = fetch_eastmoney_data(["000001", "000002", "600000"])
    print(json.dumps(data, ensure_ascii=False, indent=2))