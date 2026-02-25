import pandas as pd
import numpy as np

class StrategyEngine:
    def __init__(self, config):
        self.ma_fast = config['strategy']['ma_fast']  # 5
        self.ma_slow = config['strategy']['ma_slow']  # 20
        self.vol_ratio = config['strategy']['volume_ratio'] # 1.5
        self.hard_stop = config['strategy']['stop_loss_pct'] # -0.05

    def analyze(self, df_kline, realtime_data):
        """
        核心分析逻辑
        :param df_kline: 历史K线 DataFrame
        :param realtime_data: 实时行情 Dict
        :return: 决策字典
        """
        # 1. 确保数据是最新的
        # 如果实时价格和K线最后一行不一样，先把实时数据追加进去做计算
        latest_price = realtime_data['price']
        
        # 计算技术指标
        df = df_kline.copy()
        df['MA5'] = df['Close'].rolling(window=self.ma_fast).mean()
        df['MA20'] = df['Close'].rolling(window=self.ma_slow).mean()
        df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
        
        # 获取最新的指标值
        current_ma5 = df['MA5'].iloc[-1]
        current_ma20 = df['MA20'].iloc[-1]
        current_vol = realtime_data['volume']
        avg_vol = df['Vol_MA5'].iloc[-2] # 用昨天的均量对比，避免今天还没收盘导致偏差
        
        # --- 信号判定逻辑 (All-in 风格) ---
        
        signal = "HOLD"
        reason = []
        
        # A. 卖出逻辑 (优先级最高)
        # 1. 价格跌破 MA5 (趋势破坏)
        if latest_price < current_ma5:
            signal = "SELL"
            reason.append(f"跌破生命线 MA5 ({current_ma5:.2f})")
            
        # 2. 均线死叉 (MA5 下穿 MA20)
        if current_ma5 < current_ma20:
            signal = "SELL"
            reason.append(f"均线死叉 (MA5 < MA20)")
            
        # B. 买入逻辑 (必须极其苛刻)
        # 1. 站上 MA5
        # 2. MA5 > MA20 (多头排列)
        # 3. 放量 (量比 > 1.5)
        if signal != "SELL": # 只有没触发卖出时才看买入
            if (latest_price > current_ma5) and (current_ma5 > current_ma20):
                vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
                
                if vol_ratio > self.vol_ratio:
                    signal = "BUY"
                    reason.append(f"放量突破 (量比 {vol_ratio:.1f})")
                else:
                    reason.append(f"缩量上涨 (量比 {vol_ratio:.1f} < {self.vol_ratio})，建议观望")
            else:
                 reason.append("趋势不明或处于空头压制")

        return {
            "signal": signal, # BUY / SELL / HOLD
            "price": latest_price,
            "ma5": round(current_ma5, 2),
            "ma20": round(current_ma20, 2),
            "change_pct": realtime_data['change_pct'],
            "reasons": "; ".join(reason)
        }