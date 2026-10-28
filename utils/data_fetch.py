import efinance as ef
import pandas as pd
import requests
import os

# 缓存路径配置
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data_cache', 'history')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_realtime_data(stock_codes: list):
    """
    获取实时行情快照 (修复版：确保 open_price 定义正确)
    """
    result = {}
    
    for code in stock_codes:
        try:
            # 1. 拉取单只股票
            df = ef.stock.get_quote_snapshot(code)
            
            if df is None:
                continue
                
            if isinstance(df, pd.Series):
                df = df.to_frame().T
            
            if df.empty:
                continue
            
            row = df.iloc[0]
            
            # 2. 数据清洗与提取
            # 必须先判断最新价是否有效
            if pd.isna(row['最新价']) or str(row['最新价']) == '-':
                continue

            # === 关键修复：先定义变量，再放入字典 ===
            try:
                # 尝试获取今开，如果也是 '-' 或空，就用最新价顶替
                raw_open = row.get('今开', 0)
                if str(raw_open) == '-' or pd.isna(raw_open):
                    open_price = float(row['最新价'])
                else:
                    open_price = float(raw_open)
            except:
                # 万一转换失败，保底用最新价
                open_price = float(row['最新价'])

            # 3. 存入结果
            result[str(code)] = {
                'name': str(row['名称']),
                'price': float(row['最新价']),
                'pct': float(row['涨跌幅']),
                'high': float(row['最高']),
                'low': float(row['最低']),
                'open': open_price,       # <--- 现在这里肯定安全了
                'vol': float(row['成交量']),
                'amount': float(row['成交额'])
            }
            
        except Exception as e:
            # 打印具体变量名错误，方便调试
            print(f"DEBUG: 获取 {code} 失败: {e}")
            continue
            
    return result

def update_kline_data(stock_code: str, freq=101):
    """
    获取并缓存K线数据
    """
    try:
        df = ef.stock.get_quote_history(stock_code, klt=freq, limit=200)
        
        if df is None or df.empty:
            return None

        rename_map = {
            '日期': 'date', '开盘': 'open', '收盘': 'close', 
            '最高': 'high', '最低': 'low', '成交量': 'volume',
            '涨跌幅': 'pct_chg', '换手率': 'turnover'
        }
        df.rename(columns=rename_map, inplace=True)
        
        file_path = os.path.join(CACHE_DIR, f"{stock_code}.csv")
        df.to_csv(file_path, index=False)
        
        return df
    except Exception as e:
        print(f"DEBUG: K线获取失败 {stock_code}: {e}")
        return None

def get_stock_news(stock_code, top_n=3):
    """
    获取个股最新新闻 (原生爬虫版)
    """
    try:
        url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
        params = {
            "sr": "-1", "page_size": top_n, "page_index": 1, 
            "ann_type": "A", "client_source": "web", 
            "stock_list": stock_code, "f_node": "0", "s_node": "0" 
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        res = requests.get(url, params=params, headers=headers, timeout=5)
        data = res.json()
        
        news_list = []
        if "data" in data and "list" in data["data"]:
            for item in data["data"]["list"]:
                title = item.get("title", "")
                date = item.get("notice_date", "")[:10]
                if title:
                    news_list.append(f"[{date}] {title}")
        return news_list
    except:
        return []