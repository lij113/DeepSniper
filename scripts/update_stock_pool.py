import os
import sys
import json
import time
import requests
import concurrent.futures
from datetime import datetime
from contextlib import contextmanager
import pandas as pd
import numpy as np
import efinance as ef
from typing import Dict

# --- 1. 环境路径设置 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.append(PROJECT_ROOT)

from utils.logger import sys_logger

# --- 2. 常量定义 ---
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config', 'config.json')
STOCK_POOL_PATH = os.path.join(PROJECT_ROOT, 'config', 'stock_pool.json')

DEFAULT_MAIN_SIZE = 10
DEFAULT_WATCH_SIZE = 10

# --- 3. 核心网络工具 ---

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

@contextmanager
def no_proxy():
    """
    🛡️ 关键函数：强制直连上下文
    """
    proxies = {key: os.environ.get(key) for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']}
    for key in proxies:
        if key in os.environ: del os.environ[key]
    try:
        yield
    finally:
        for key, value in proxies.items():
            if value and key not in os.environ: os.environ[key] = value

def fetch_and_set_proxy(conf: dict):
    """
    [增强版] 访问代理 API，提取 IP 并设置环境变量
    """
    api_url = conf.get('network', {}).get('proxy_api_url')
    
    if not api_url:
        hp = conf.get('network', {}).get('http_proxy')
        if hp:
            os.environ['http_proxy'] = hp
            os.environ['https_proxy'] = hp
            sys_logger.info("🌐 使用静态代理配置")
            return True
        sys_logger.warning("⚠️ 未配置代理 API，尝试直连...")
        return True

    # 清理旧代理
    for k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
        if k in os.environ: del os.environ[k]

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            with no_proxy():
                if attempt > 1:
                    sys_logger.info(f"🔄 第 {attempt} 次尝试提取新代理...")
                
                resp = requests.get(
                    api_url, 
                    timeout=8, 
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                data = resp.json()

            if data.get('code') == 'SUCCESS' or data.get('code') == 0:
                proxy_list = data.get('data', [])
                if proxy_list:
                    item = proxy_list[0]
                    ip = item.get('ip') or item.get('server')
                    port = item.get('port')
                    
                    if port:
                        full_proxy = f"http://{ip}:{port}"
                    else:
                        full_proxy = f"http://{ip}"

                    os.environ['http_proxy'] = full_proxy
                    os.environ['https_proxy'] = full_proxy
                    sys_logger.info(f"✅ 已切换新代理: {full_proxy}")
                    return True
            else:
                sys_logger.warning(f"⚠️ 提取失败: {data}")

        except Exception as e:
            sys_logger.warning(f"⚠️ 提取异常 (尝试 {attempt}): {e}")
        
        time.sleep(2)

    sys_logger.error("❌ 代理获取彻底失败，系统将尝试裸奔 (直连)")
    return False

# --- 4. 稳健的数据获取 ---

def get_market_snapshot_safe(conf):
    """
    🛡️ 带自动换IP重试机制的行情抓取
    """
    retries = 3
    for i in range(retries):
        try:
            df = ef.stock.get_realtime_quotes()
            if df is not None and not df.empty:
                return df
            else:
                sys_logger.warning(f"⚠️ 获取行情为空 (第 {i+1} 次)")
        except Exception as e:
            sys_logger.warning(f"⚠️ 获取行情网络报错: {e}")
        
        sys_logger.info("♻️ 正在更换 IP 重试...")
        fetch_and_set_proxy(conf)
        time.sleep(2)
    
    return None

# --- 5. 核心技术分析模块（大幅增强） ---

def calculate_indicators(df_hist: pd.DataFrame) -> Dict:
    if df_hist is None or len(df_hist) < 40: return None  # ADX需要更长周期
    df = df_hist.sort_values(by='日期', ascending=True).copy()
    
    # 基础均线 & 量
    df['MA5'] = df['收盘'].rolling(5).mean()
    df['MA10'] = df['收盘'].rolling(10).mean()
    df['MA20'] = df['收盘'].rolling(20).mean()
    df['Vol_MA5'] = df['成交量'].rolling(5).mean()
    
    # RSI14
    delta = df['收盘'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # ADX (趋势强度，需要+DI -DI)
    high_diff = df['最高'].diff()
    low_diff = df['最低'].diff()
    tr = pd.concat([
        df['最高'] - df['最低'],
        (df['最高'] - df['收盘'].shift()).abs(),
        (df['最低'] - df['收盘'].shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    
    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = (-low_diff).where((low_diff > high_diff) & (low_diff > 0), 0)
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/14).mean() / atr)
    
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    df['ADX'] = dx.ewm(alpha=1/14).mean()
    
    # 近期收益
    recent_return = (df['收盘'].iloc[-1] / df['收盘'].iloc[-10] - 1) if len(df) >= 10 else 0
    
    return {
        **df.iloc[-1].to_dict(),
        "recent_return": recent_return
    }

def analyze_single_stock(stock_info: Dict, filters: Dict, market_hot: float):
    code = stock_info['股票代码']
    name = stock_info['股票名称']
    daily_rise = stock_info.get('涨跌幅', 0)
    price_today = stock_info.get('最新价', 0)  # 实时行情最新价
    
    for _ in range(2):
        try:
            df_hist = ef.stock.get_quote_history(code, klt=101, limit=80)  # 拉长到80日支持ADX
            if df_hist is None or df_hist.empty: continue

            last_k = calculate_indicators(df_hist)
            if last_k is None: return None
            
            price = last_k['收盘']
            ma5 = last_k['MA5']
            ma20 = last_k['MA20']
            rsi = last_k['RSI']
            adx = last_k.get('ADX', 0)
            vol = last_k['成交量']
            vol_ma5 = last_k['Vol_MA5']
            turnover = df_hist.iloc[-1].get('换手率', 0)
            
            if pd.isna(ma20) or pd.isna(rsi) or pd.isna(adx): return None
            
            # --- 动态筛选逻辑 ---
            is_uptrend = ma5 > ma20
            is_strong = price > ma20
            is_vol_ok = vol > vol_ma5 * filters.get('vol_ma_multiplier', 0.8)
            is_rsi_good = filters.get('rsi_low', 50) < rsi < filters.get('rsi_high', 85)
            is_adx_good = adx > filters.get('min_adx', 20)  # 趋势确立
            
            if is_uptrend and is_strong and is_rsi_good and is_vol_ok and is_adx_good:
                score = 0
                score += rsi * 2
                score += (price / ma5) * 100
                score += last_k['recent_return'] * 200
                score += turnover * 12  # 换手权重略增
                score += (price / ma20 - 1) * 300
                score += adx * 5  # ADX高加分（强趋势）
                
                # 动态惩罚近期涨幅（市场热时可容忍更高）
                max_recent = 0.4 if market_hot > 0 else 0.3
                if last_k['recent_return'] > max_recent:
                    score -= (last_k['recent_return'] - max_recent) * 200
                
                # 当日涨幅软惩罚（市场热时放宽）
                score -= daily_rise * (30 if market_hot > 0 else 50)
                
                # 价格过滤奖励（避低价股）
                if price_today < 5:
                    return None  # 直接剔除<5元股
                elif price_today > 20:
                    score += 100  # 高价股（相对优质）加分
                
                return {
                    "code": code,
                    "name": name,
                    "score": round(score, 2),
                    "price": price,
                    "rsi": round(rsi, 2),
                    "adx": round(adx, 2),
                    "turnover": round(turnover, 2),
                    "daily_rise": round(daily_rise, 2)
                }
            break
        except Exception as e:
            sys_logger.debug(f"单股分析异常 {code}: {e}")
            time.sleep(0.5)
            continue
    return None

# --- 6. 选股主流程（核心改进） ---

def filter_and_select(df: pd.DataFrame, main_size: int, watch_size: int, config: Dict):
    if df is None or df.empty: return [], []
    
    start_time = time.time()
    filters = config.get('stock_pool_filters', {})

    # 1. 主板 + 去除ST + 基本清洗
    df['股票代码'] = df['股票代码'].astype(str).str.zfill(6)
    df = df[df['股票代码'].str.match(r'^(60|00)')]
    df = df[~df['股票名称'].str.contains('ST|退', na=False)]
    
    # 新增：闭市后关键修复
    df.replace('--', np.nan, inplace=True)
    
    for col in ['成交额', '涨跌幅', '量比', '换手率', '最新价']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    
    # 计算市场热度（涨停家数 / 总股票 > 2% 为热，否则冷）
    total_stocks = len(df)
    up_limit_count = len(df[df['涨跌幅'] >= 9.5])
    market_hot = 1 if (total_stocks > 0 and up_limit_count / total_stocks > 0.02) else 0 
    sys_logger.info(f"🌡️ 市场热度检测：涨停{up_limit_count}家，判定{'热点活跃' if market_hot else '偏冷调整'}")
    
    
    # 动态调整当日涨幅上限
    dynamic_max_rise = filters.get('hot_max_daily_rise', 6.0) if market_hot else filters.get('max_daily_rise', 4.0)
    
    # 2. 门槛过滤（动态）
    df = df[df['成交额'] > filters.get('min_turnover_amount', 20000000)]
    df = df[df['最新价'] > 5.0]  # 硬过滤低价股
    df = df[(df['涨跌幅'] > filters.get('min_daily_rise', -8.0)) & 
            (df['涨跌幅'] <= dynamic_max_rise)]
    
    # 3. 多路径初选（增强热点路径）
    high_turnover = df[df['换手率'] > filters.get('min_turnover_rate', 4.0)]  # 略降门槛
    strong_movers = df[(df['量比'] > (filters.get('hot_volume_ratio', 2.5) if market_hot else filters.get('min_volume_ratio', 1.8)))]
    mild_up = df[(df['涨跌幅'] > 0) & (df['量比'] > 1.2) & (df['换手率'] > 2.5)]
    
    candidates_df = pd.concat([high_turnover, strong_movers, mild_up]).drop_duplicates(subset=['股票代码'])
    
    # 动态候选池大小
    max_cand = filters.get('hot_max_candidates', 200) if market_hot else filters.get('max_candidates', 120)
    candidates_df = candidates_df.head(max_cand)
    
    sys_logger.info(f"🔍 候选池：{len(candidates_df)} 只（动态上限 {dynamic_max_rise}% 涨幅） -> 技术扫描")
    
    candidates_list = candidates_df.to_dict('records')
    final_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:  # 线程略增
        futures = [executor.submit(analyze_single_stock, stock, filters, market_hot) for stock in candidates_list]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: final_results.append(res)
    
    sys_logger.info(f"✅ 技术符合: {len(final_results)} 只 (耗时: {time.time() - start_time:.1f}s)")
    
    final_results.sort(key=lambda x: x['score'], reverse=True)
    
    if final_results:
        top3 = final_results[:3]
        log_msg = ", ".join([f"{x['name']}(分:{x['score']}, ADX:{x['adx']}, 涨:{x['daily_rise']}%)" for x in top3])
        sys_logger.info(f"🔥 强势TOP3: {log_msg}")
    
    all_codes = [x['code'] for x in final_results]
    
    # 补池优化：优先补正涨幅、高换手票
    need = main_size + watch_size - len(all_codes)
    if need > 0:
        existing = set(all_codes)
        supplement = df[
            (~df['股票代码'].isin(existing)) &
            (df['涨跌幅'] > 0) &
            (df['换手率'] > 3)
        ].sort_values(by=['换手率', '成交额'], ascending=False)
        all_codes.extend(supplement['股票代码'].tolist()[:need])
    
    return all_codes[:main_size], all_codes[main_size:main_size + watch_size]

def update_stock_pool_once(config):
    fetch_and_set_proxy(config)
    
    params = config.get('strategy_params', {})
    m_size = params.get('MAIN_POOL_SIZE', DEFAULT_MAIN_SIZE)
    w_size = params.get('WATCH_POOL_SIZE', DEFAULT_WATCH_SIZE)
    
    df = get_market_snapshot_safe(config)
    
    if df is None:
        sys_logger.error("❌ 多次重试后仍无法获取市场行情，跳过本次更新")
        return
    
    main_pool, watch_pool = filter_and_select(df, m_size, w_size, config)
    
    payload = {
        "main_pool": main_pool,
        "watch_pool": watch_pool,
        "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    try:
        with open(STOCK_POOL_PATH, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)
        sys_logger.info(f"💾 股票池更新完毕：主池 {len(main_pool)} | 观察池 {len(watch_pool)}")
    except Exception as e:
        sys_logger.error(f"❌ 写入 stock_pool.json 失败: {e}")

# --- 7. 独立调度入口 ---

if __name__ == "__main__":
    sys_logger.info(">>> 股票池更新服务 (Run Once) <<<")
    conf = load_config()
    update_stock_pool_once(conf)