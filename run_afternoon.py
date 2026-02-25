import yaml
from core.data_fetcher import data_fetcher
from core.strategy import StrategyEngine
from core.llm_client import llm_client
from core.notifier import notifier
from config.prompts import Prompts

def main():
    print("🚀 DeepSniper 尾盘扫描启动...")
    
    # 1. 加载配置
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    symbol = config['target']['stock_codes'][0]
    stock_name = config['target']['stock_name']
    
    # 2. 获取数据 (Data)
    df_kline = data_fetcher.get_kline(symbol)
    realtime = data_fetcher.get_realtime_price(symbol)
    news_text = data_fetcher.get_stock_news(symbol)
    
    if realtime is None:
        print("❌ 无法获取行情，任务终止")
        return

    # 3. 运行策略 (Math)
    engine = StrategyEngine(config)
    strategy_res = engine.analyze(df_kline, realtime)
    
    # 4. 运行AI (Brain)
    print("🧠 正在请求 DeepSeek 进行最终裁决...")
    
    # 【新增】准备盘面数据字符串
    tech_info = f"{strategy_res['signal']} (MA5={strategy_res['ma5']})"
    
    ai_res = llm_client.get_analysis(
        Prompts.SENTIMENT_ANALYSIS,
        persona=Prompts.TRADER_PERSONA,
        stock_name=stock_name,
        # 【新增】传入盘面数据
        change_pct=realtime['change_pct'],
        price=realtime['price'],
        technical_signal=tech_info,
        news_content=news_text[:1500]
    )
    
    # 5. 生成报告
    report = notifier.generate_report(stock_name, strategy_res, ai_res, news_text)
    
    # 打印到屏幕 (让你在实验室一眼看到)
    print("\n" + "="*50)
    print(report)
    print("="*50)

if __name__ == "__main__":
    main()