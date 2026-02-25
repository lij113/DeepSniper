from core.data_fetcher import data_fetcher

def test_eyes():
    symbol = "603619" # 中曼石油
    
    # 1. 测试历史K线
    df = data_fetcher.get_kline(symbol)
    if df is not None:
        print(f"\n✅ 成功获取历史K线，最后一天: {df.index[-1].date()}, 收盘价: {df.iloc[-1]['Close']}")
    
    # 2. 测试实时行情
    realtime = data_fetcher.get_realtime_price(symbol)
    if realtime:
        print(f"✅ 成功获取实时价格: {realtime['price']} (涨跌幅: {realtime['change_pct']}%)")
    
    # 3. 测试新闻
    news = data_fetcher.get_stock_news(symbol)
    if news:
        print(f"\n✅ 个股新闻获取成功 (前50字):\n{news[:50]}...")

if __name__ == "__main__":
    test_eyes()