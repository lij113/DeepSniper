import pandas as pd
import numpy as np

# --- 1. 基础计算工具 ---

def _to_numeric(df, cols):
    """使用 float32 优化内存并加速向量化运算"""
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').astype(np.float32)
    return df

def _ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def _tr(df):
    """计算 True Range (真实波幅)"""
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    return pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

# --- 2. 核心指标算法 ---

def _rsi(series, period=14):
    """修正：使用 Wilder's Smoothing 平滑算法，与主流软件数值对齐"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    # Wilder's 平滑
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(0)

def _macd(series, fast=12, slow=26, signal=9):
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    diff = ema_fast - ema_slow
    dea = _ema(diff, signal)
    hist = (diff - dea) * 2 # A股习惯乘2看柱状图
    return diff, dea, hist

def _kdj(df, n=9, k_period=3, d_period=3):
    low_n = df['low'].rolling(n).min()
    high_n = df['high'].rolling(n).max()
    rsv = (df['close'] - low_n) / (high_n - low_n) * 100
    k = rsv.ewm(alpha=1 / k_period, adjust=False).mean()
    d = k.ewm(alpha=1 / d_period, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j

def _adx(df, period=14):
    """平均趋向指数：用于过滤震荡市，ADX > 25 代表强趋势"""
    plus_dm = np.where((df['high'].diff() > df['low'].shift(1) - df['low']) & (df['high'].diff() > 0), df['high'].diff(), 0)
    minus_dm = np.where((df['low'].shift(1) - df['low'] > df['high'].diff()) & (df['low'].shift(1) - df['low'] > 0), df['low'].shift(1) - df['low'], 0)
    
    tr = _tr(df).rolling(period).mean()
    plus_di = 100 * (pd.Series(plus_dm).rolling(period).mean() / tr)
    minus_di = 100 * (pd.Series(minus_dm).rolling(period).mean() / tr)
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di)).fillna(0)
    return dx.rolling(period).mean(), plus_di, minus_di

def _supertrend(df, period=7, multiplier=3):
    """SuperTrend：经典的趋势追踪指标，适合右侧交易"""
    atr = _tr(df).rolling(period).mean()
    hl2 = (df['high'] + df['low']) / 2
    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)
    
    # 趋势状态数组
    is_uptrend = np.ones(len(df), dtype=bool)
    for i in range(1, len(df)):
        if df['close'].iloc[i] > upperband.iloc[i-1]:
            is_uptrend[i] = True
        elif df['close'].iloc[i] < lowerband.iloc[i-1]:
            is_uptrend[i] = False
        else:
            is_uptrend[i] = is_uptrend[i-1]
    return is_uptrend, upperband, lowerband

# --- 3. 综合计算入口 ---

def compute_indicators(kline_df: pd.DataFrame):
    if kline_df is None or kline_df.empty: return {}

    df = kline_df.copy()
    df = _to_numeric(df, ['open', 'high', 'low', 'close', 'volume'])

    # 1. 均线系统
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()

    # 2. 趋势与强度
    adx, pdi, mdi = _adx(df)
    is_uptrend, st_upper, st_lower = _supertrend(df)
    
    # 3. 摆动指标
    diff, dea, hist = _macd(df['close'])
    rsi6 = _rsi(df['close'], 6)
    rsi12 = _rsi(df['close'], 12)
    k, d, j = _kdj(df)

    # 4. 量能指标
    vol_ma5 = df['volume'].rolling(5).mean()
    vol_ratio = df['volume'] / vol_ma5.replace(0, np.nan)

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    # 构建返回字典
    # 【关键修复】所有 numpy 类型必须显式转换为 Python 原生类型 (float, bool)
    indicators = {
        "close": float(latest['close']),
        "ma5": float(latest['ma5']) if pd.notna(latest['ma5']) else None,
        "ma20": float(latest['ma20']) if pd.notna(latest['ma20']) else None,
        "ma60": float(latest['ma60']) if pd.notna(latest['ma60']) else None,
        "macd_hist": float(hist.iloc[-1]),
        "macd_status": "GOLD" if (hist.iloc[-1] > 0 and hist.iloc[-2] <= 0) else "DEATH" if (hist.iloc[-1] < 0 and hist.iloc[-2] >= 0) else "NONE",
        "rsi12": float(rsi12.iloc[-1]),
        "kdj_j": float(j.iloc[-1]),
        "adx": float(adx.iloc[-1]) if pd.notna(adx.iloc[-1]) else 0,
        "trend_direction": "UP" if is_uptrend[-1] else "DOWN",
        "vol_ratio": float(vol_ratio.iloc[-1]) if pd.notna(vol_ratio.iloc[-1]) else 1.0,
        
        # 👇 关键修复点：包裹 bool() 强制转换
        "is_overbought": bool(rsi6.iloc[-1] > 80 or j.iloc[-1] > 100),
        "is_oversold": bool(rsi6.iloc[-1] < 20 or j.iloc[-1] < 0)
    }
    return indicators

# --- 4. 形态识别系统 ---

def detect_candlestick_patterns(kline_df: pd.DataFrame):
    """
    形态识别：引入量能确认和趋势上下文
    """
    if kline_df is None or len(kline_df) < 5: return []

    df = kline_df.tail(5).copy()
    df = _to_numeric(df, ['open', 'high', 'low', 'close', 'volume'])

    c2 = df.iloc[-2] # 前一日
    c3 = df.iloc[-1] # 今日

    def body(c): return abs(c['close'] - c['open'])
    def range_(c): return max(c['high'] - c['low'], 1e-9)

    patterns = []

    # 1. 看涨吞没 + 放量确认
    if (c2['close'] < c2['open']) and (c3['close'] > c3['open']):
        if c3['close'] >= c2['open'] and c3['open'] <= c2['close']:
            tag = "放量看涨吞没" if c3['volume'] > c2['volume'] * 1.5 else "看涨吞没"
            patterns.append(tag)

    # 2. 十字星 (判断犹豫/变盘)
    if body(c3) / range_(c3) < 0.1:
        patterns.append("十字星")

    # 3. 锤头线 (低位企稳信号)
    lower_shadow = min(c3['close'], c3['open']) - c3['low']
    upper_shadow = c3['high'] - max(c3['close'], c3['open'])
    if lower_shadow > 2 * body(c3) and upper_shadow < body(c3):
        patterns.append("锤头线")
	
	# 4. === [新增] 游资核心：N型反包/弱转强结构 ===
    # 逻辑：前天/大前天有大涨 -> 昨天回调(分歧) -> 今天反包(一致)
    try:
        # 获取最近4天数据
        recent = df.tail(4)
        if len(recent) >= 3:
            p_chg = recent['close'].pct_change()
            
            # 今天 (iloc[-1])
            today_strong = p_chg.iloc[-1] > 0.04  # 今天至少涨4%
            
            # 昨天 (iloc[-2])
            yesterday_weak = p_chg.iloc[-2] < 0   # 昨天是绿盘（洗盘）
            
            # 前天 (iloc[-3]) 或 大前天
            prev_strong = p_chg.iloc[-3] > 0.05   # 前天是大阳线
            
            # 关键：缩量回调 (昨量 < 前量)
            vol_shrink = recent['volume'].iloc[-2] < recent['volume'].iloc[-3]
            
            if today_strong and yesterday_weak and prev_strong:
                if vol_shrink:
                    patterns.append("标准N型反包(缩量回调)")
                else:
                    patterns.append("N型反包(空中加油)")
    except Exception as e:
        pass # 防止数据不足报错

    return list(dict.fromkeys(patterns))