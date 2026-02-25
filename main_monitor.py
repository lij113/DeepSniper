import sys
import yaml
from datetime import datetime
from core.screener import Screener
from core.data_fetcher import data_fetcher
from core.strategy import StrategyEngine
from core.llm_client import llm_client
from config.prompts import Prompts

def load_config():
    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f)

def generate_advice(action, price_desc, operation_desc):
    """标准化输出格式"""
    return f"""
【操作建议】：{action}
【期望价格】：{price_desc}
【具体操作】：{operation_desc}
    """

def run_system(mode="morning"):
    """
    mode: 'morning' (早盘 09:00) 或 'afternoon' (尾盘 14:20)
    """
    config = load_config()
    status = config['account']['status']
    
    print(f"🔥 系统启动 | 模式: {mode} | 当前状态: {status}")
    
    # ==========================
    # 场景 A: 持仓防守模式 (HOLDING)
    # ==========================
    if status == "HOLDING":
        symbol = config['account']['holding_symbol']
        cost = config['account']['holding_cost']
        print(f"🛡️ 进入持仓监控: {symbol} (成本 {cost})")
        
        # 1. 获取数据
        realtime = data_fetcher.get_realtime_price(symbol)
        news = data_fetcher.get_stock_news(symbol)
        df_kline = data_fetcher.get_kline(symbol)
        
        # 2. 策略计算 (Strategy)
        engine = StrategyEngine(config)
        strat_res = engine.analyze(df_kline, realtime) # 算 MA5 破位没
        
        # 3. AI 分析 (Brain)
        ai_res = llm_client.get_analysis(
            Prompts.SENTIMENT_ANALYSIS,
            # 【修复 1】补上 persona 参数
            persona=Prompts.TRADER_PERSONA,
            stock_name=symbol,
            change_pct=realtime['change_pct'],
            price=realtime['price'],
            technical_signal=strat_res['signal'],
            news_content=news[:1000]
        )
        
        # 4. 生成建议
        action = "持股不动"
        price_exp = "无"
        detail = "趋势良好，继续持有。"
        
        # 止损/止盈逻辑
        if strat_res['signal'] == "SELL":
            action = "卖出 (止损/止盈)"
            price_exp = "市价 (竞价或尾盘直接走)"
            detail = f"触发技术面卖点: {strat_res['reasons']}。AI观点: {ai_res.get('score')}"
        elif ai_res.get('score', 0) < -0.6:
            action = "卖出 (避险)"
            detail = f"技术面虽未破位，但AI识别到重大利空: {ai_res.get('reason')}"
            
        print(generate_advice(action, price_exp, detail))

    # ==========================
    # 场景 B: 空仓进攻模式 (EMPTY)
    # ==========================
    elif status == "EMPTY":
        print(f"⚔️ 进入选股进攻模式 (目标: 主板 Top 50)")
        
        # 1. 扫描全市场 (Screener)
        screener = Screener(config)
        candidates = screener.scan_opportunities() # 返回 ~50 只股票
        
        print(f"🔍 筛选出 {len(candidates)} 只技术面强势股，AI 正在批阅...")
        
        best_pick = None
        best_score = -99
        
        # 2. AI 优中选优 (只看前 5-10 个，省 API 钱且快)
        for stock in candidates[:10]:
            print(f"🤖 分析: {stock['name']} ({stock['symbol']})...")
            
            # 抓新闻
            news = data_fetcher.get_stock_news(stock['symbol'])
            
            # AI 打分
            ai_res = llm_client.get_analysis(
                Prompts.SENTIMENT_ANALYSIS,
                # 【修复 2】补上 persona 参数
                persona=Prompts.TRADER_PERSONA,
                stock_name=stock['name'],
                change_pct=stock['change_pct'],
                price=stock['price'],
                technical_signal="多头排列,放量",
                news_content=news[:800]
            )
            
            score = ai_res.get('score', 0)
            if score > best_score and score > 0.3: # 必须要正向分数
                best_score = score
                best_pick = {
                    "stock": stock,
                    "ai_reason": ai_res.get('reason'),
                    "score": score
                }
        
        # 3. 生成建议
        if best_pick:
            stock = best_pick['stock']
            action = f"买进 {stock['name']} ({stock['symbol']})"
            
            if mode == "morning":
                price_exp = "关注开盘竞价，若高开 < 3% 且量比 > 2"
                detail = f"AI评分 {best_pick['score']}。理由: {best_pick['ai_reason']}。早盘适合观察承接力度。"
            else:
                price_exp = "尾盘 14:50 市价买入"
                detail = f"全天走势稳健，收盘大概率站稳 MA5。AI评分 {best_pick['score']}。适合博弈明日溢价。"
        else:
            action = "空仓观望"
            price_exp = "-"
            detail = "扫描前10强，未发现基本面/消息面共振的完美标的。"
            
        print(generate_advice(action, price_exp, detail))

if __name__ == "__main__":
    # 从命令行接收参数: python main_monitor.py morning
    mode = sys.argv[1] if len(sys.argv) > 1 else "afternoon"
    run_system(mode)