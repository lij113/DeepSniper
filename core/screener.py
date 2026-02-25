import time
import pandas as pd
# 👇 【关键修正】这里必须导入 data_fetcher 实例
from core.data_fetcher import retry, data_fetcher 

class Screener:
    def __init__(self, config):
        self.config = config

    def is_main_board(self, symbol):
        """判断是否为主板 (60开头沪市主板, 00开头深市主板)"""
        s = str(symbol)
        return s.startswith("60") or s.startswith("00")

    def scan_opportunities(self):
        # 1. 获取全市场快照 (调用 Tushare)
        df_spot = data_fetcher.get_market_snapshot_fast()
        
        if df_spot is None or df_spot.empty:
            print("❌ 无法获取市场行情，跳过本次扫描")
            return []

        candidates = []
        # Tushare get_today_all 返回的数据列名：code, name, changepercent, trade, ...
        for index, row in df_spot.iterrows():
            try:
                symbol = str(row['code'])
                name = row['name']
                price = row['trade']
                change_pct = row['changepercent']
                turnover = row['turnoverratio']
                
                # Tushare 有时候会返回空值，做个保护
                if pd.isna(price) or pd.isna(change_pct):
                    continue

                # --- 过滤逻辑 ---
                if not self.is_main_board(symbol): continue 
                if "ST" in name: continue 
                if price < self.config['scanner']['min_price']: continue
                if change_pct < 2.0: continue # 必须是涨势
                if turnover < self.config['scanner']['min_turnover']: continue 
                
                candidates.append({
                    "symbol": symbol,
                    "name": name,
                    "price": price,
                    "change_pct": change_pct,
                    "turnover": turnover,
                    "volume": row['volume']
                })
            except Exception:
                continue
            
        print(f"✅ 初步筛选出 {len(candidates)} 只活跃主板股，开始技术面精筛...")
        
        # 2. Level 2 技术面精筛
        # 只处理前 20 个，防止请求太快被封
        top_candidates = sorted(candidates, key=lambda x: x['turnover'], reverse=True)[:20]
        
        final_list = []
        for stock in top_candidates:
            try:
                # 稍微 sleep 一下
                time.sleep(0.1)
                
                # 获取个股K线 (复用 data_fetcher)
                df_k = data_fetcher.get_kline(symbol=stock['symbol'])
                if df_k is None or df_k.empty: continue
                
                closes = df_k['Close'].values
                if len(closes) < 20: continue
                
                ma5 = closes[-5:].mean()
                ma20 = closes[-20:].mean()
                current_price = stock['price']
                
                # 核心选股逻辑: 多头排列 + 没涨飞
                if current_price > ma5 and ma5 > ma20 and stock['change_pct'] < 9.5:
                    stock['MA5'] = ma5
                    stock['MA20'] = ma20
                    final_list.append(stock)
                    print(f"🎯 命中目标: {stock['name']} (+{stock['change_pct']}%)")
                    
            except Exception as e:
                # print(f"⚠️ 跳过 {stock['name']}: {e}") # 调试时可以打开
                continue
                
        return final_list[:10]