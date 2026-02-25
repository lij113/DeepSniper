import pandas as pd
import efinance as ef
import time
from functools import wraps
from datetime import datetime

# ==========================================
# Retry 装饰器 (保留你的稳健性)
# ==========================================
def retry(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"⚠️ [{func.__name__}] 波动重试 ({i+1}/{max_retries}): {e}")
                    time.sleep(delay)
            print(f"❌ [{func.__name__}] 彻底失败")
            return None
        return wrapper
    return decorator

class DataFetcher:
    def __init__(self):
        pass

    @retry()
    def get_kline(self, symbol="603619", period="daily", start_date="20250101"):
        """
        获取历史K线 (使用 eFinance)
        速度极快，且自动处理复权
        """
        # eFinance 不需要后缀，只要数字代码
        code = symbol.split(".")[0]
        
        # 101 代表日线
        klt = 101 
        
        # ef 返回的是 DataFrame
        df = ef.stock.get_quote_history(code, klt=klt)
        
        if df is None or df.empty:
            return None

        # 清洗列名以适配 DeepSniper
        # eFinance 列名: 股票名称, 股票代码, 日期, 开盘, 收盘, 最高, 最低, 成交量, ...
        df = df.rename(columns={
            '日期': 'Date',
            '开盘': 'Open',
            '收盘': 'Close',
            '最高': 'High',
            '最低': 'Low',
            '成交量': 'Volume'
        })
        
        # 筛选时间
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        # 截取 start_date 之后的数据
        df = df[df.index >= pd.to_datetime(start_date)]
        
        return df

    @retry()
    def get_realtime_price(self, symbol="603619"):
        """
        获取实时行情 (使用 eFinance)
        """
        code = symbol.split(".")[0]
        
        # get_latest_quote 可以一次查一个或多个
        df = ef.stock.get_latest_quote([code])
        
        if df is None or df.empty:
            return None
            
        row = df.iloc[0]
        return {
            "symbol": symbol,
            "price": float(row['最新价']),
            "open": float(row['今开']),
            "change_pct": float(row['涨跌幅']),
            "high": float(row['最高']),
            "low": float(row['最低']),
            "volume": float(row['成交量'])
        }

    @retry()
    def get_market_snapshot_fast(self):
        """
        [全市场扫描]
        eFinance 的全市场扫描非常强悍，不容易超时
        """
        print("🛰️ 正在通过 eFinance 拉取全市场行情...")
        df = ef.stock.get_realtime_quotes()
        
        # 适配 Tushare/Akshare 的列名格式供 Screener 使用
        # eFinance: 股票代码, 股票名称, 涨跌幅, 最新价, ...
        df = df.rename(columns={
            '股票代码': 'code',
            '股票名称': 'name',
            '最新价': 'trade',
            '涨跌幅': 'changepercent',
            '换手率': 'turnoverratio',
            '成交量': 'volume'
        })
        
        return df

    @retry()
    def get_stock_news(self, symbol="603619"):
        """新闻部分还是保留 Akshare，因为 ef 没有新闻接口"""
        try:
            import akshare as ak
            code = symbol.split(".")[0]
            df = ak.stock_news_em(symbol=code)
            news = ""
            for _, row in df.head(3).iterrows():
                news += f"- {row['新闻标题']}\n"
            return news
        except:
            return "暂无新闻"

# 单例
data_fetcher = DataFetcher()