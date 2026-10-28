import sys
import os
import json
import time
import requests
from datetime import datetime
from contextlib import contextmanager

import pandas as pd
import efinance as ef

# --- 1. 环境路径设置 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.append(PROJECT_ROOT)

from utils.logger import sys_logger
from utils.notify import send_wechat_message
from utils.data_fetch import get_realtime_data, get_stock_news 
from utils.deepseek_api import analyze_stock_technical
from strategies.technical_analysis import compute_indicators, detect_candlestick_patterns

# --- 2. 常量定义 ---
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config', 'config.json')
STOCK_POOL_PATH = os.path.join(PROJECT_ROOT, 'config', 'stock_pool.json')
STATE_DIR = os.path.join(PROJECT_ROOT, 'data_cache', 'state')

if not os.path.exists(STATE_DIR):
    os.makedirs(STATE_DIR)

# --- 3. 辅助配置函数 ---

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- 4. 核心补丁：动态代理与直连工具 ---

@contextmanager
def no_proxy():
    """DeepSeek 直连专用：临时移除代理"""
    http_proxy = os.environ.get('http_proxy')
    https_proxy = os.environ.get('https_proxy')
    
    if 'http_proxy' in os.environ: del os.environ['http_proxy']
    if 'https_proxy' in os.environ: del os.environ['https_proxy']
    
    try:
        yield
    finally:
        if http_proxy: os.environ['http_proxy'] = http_proxy
        if https_proxy: os.environ['https_proxy'] = https_proxy

def refresh_proxy():
    """
    🔄 失败救星：主动调用 API 提取并更换新 IP
    """
    try:
        config = load_config()
        api_url = config.get('network', {}).get('proxy_api_url')
        
        if not api_url:
            sys_logger.warning("⚠️ 无法切换IP：未配置 proxy_api_url")
            return False

        # 临时直连去请求代理API
        with no_proxy():
            # 增加 User-Agent 防止被拦截
            resp = requests.get(api_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                data = resp.json()
            except:
                sys_logger.warning(f"⚠️ 代理API返回非JSON: {resp.text}")
                return False

        if data.get('code') == 'SUCCESS':
            proxy_list = data.get('data', [])
            if proxy_list:
                proxy_str = proxy_list[0].get('server')
                full_proxy = f"http://{proxy_str}"
                
                os.environ['http_proxy'] = full_proxy
                os.environ['https_proxy'] = full_proxy
                sys_logger.info(f"♻️ 已自动切换新代理: {full_proxy}")
                return True
        else:
            sys_logger.warning(f"⚠️ 切换代理失败: {data}")
            return False
            
    except Exception as e:
        sys_logger.error(f"❌ 切换代理异常: {e}")
        return False

def get_kline_safe(code, klt=101, limit=60, retries=3):
    """🛡️ K线获取：失败自动换 IP"""
    rename_map = {
        '日期': 'date', '开盘': 'open', '收盘': 'close',
        '最高': 'high', '最低': 'low', '成交量': 'volume',
        '成交额': 'amount', '涨跌幅': 'pct_chg', '换手率': 'turnover'
    }

    for i in range(retries):
        try:
            df = ef.stock.get_quote_history(code, klt=klt, limit=limit)
            if df is not None and not df.empty:
                df = df.rename(columns=rename_map)
                return df
        except Exception as e:
            sys_logger.warning(f"⚠️ {code} K线获取失败，正在换 IP 重试...")
            refresh_proxy()
            time.sleep(1) # 稍等生效
            
    return None

def get_realtime_data_safe(stock_list, retries=3):
    """
    🛡️ [新增] 实时行情获取：失败自动换 IP
    专门解决 407 Proxy Authentication Required 问题
    """
    for i in range(retries):
        try:
            # 尝试获取
            data = get_realtime_data(stock_list)
            # 如果返回非空，且不是空字典，说明成功
            if data and len(data) > 0:
                return data
            else:
                raise ValueError("获取到的行情为空")
        except Exception as e:
            sys_logger.warning(f"⚠️ 批量行情获取失败 (第{i+1}次)，正在换 IP 重试...")
            refresh_proxy()
            time.sleep(1)
            
    return {}

# --- 5. 状态管理与选股逻辑 ---

def get_today_state_file():
    today_str = datetime.now().strftime('%Y-%m-%d')
    return os.path.join(STATE_DIR, f"signals_{today_str}.json")

def load_sent_signals():
    file_path = get_today_state_file()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_signal(stock_code, signal_type):
    signals = load_sent_signals()
    signals[stock_code] = signal_type
    with open(get_today_state_file(), 'w', encoding='utf-8') as f:
        json.dump(signals, f, ensure_ascii=False)

def get_target_stocks(config):
    if os.path.exists(STOCK_POOL_PATH):
        try:
            with open(STOCK_POOL_PATH, 'r', encoding='utf-8') as f:
                pool = json.load(f)
                if 'main_pool' in pool and pool['main_pool']:
                    sys_logger.info(f"✅ 已加载 stock_pool.json，包含 {len(pool['main_pool'])} 只主力标的")
                    return pool['main_pool']
                elif 'watch_pool' in pool and pool['watch_pool']:
                    sys_logger.info(f"✅ 已加载 stock_pool.json，包含 watch_pool {len(pool['watch_pool'])} 只标的")
                    return pool['watch_pool']
                elif 'active' in pool and pool['active']:
                    return pool['active']
        except Exception as e:
            sys_logger.error(f"❌ 读取 stock_pool.json 失败: {e}")

    if 'stock_pool' in config:
        if 'main_pool' in config['stock_pool']:
            return config['stock_pool']['main_pool']
        if 'active' in config['stock_pool']:
            return config['stock_pool']['active']

    return ["600519"]

# --- 6. 核心分析流程 ---

def run_deep_sniper_analysis():
    sys_logger.info(">>> DeepSniper 执行 (全链路自动换IP版) <<<")
    
    try:
        config = load_config()
        stock_list = get_target_stocks(config)
        
        # 合并观察池
        if os.path.exists(STOCK_POOL_PATH):
            try:
                with open(STOCK_POOL_PATH, 'r', encoding='utf-8') as f:
                    pool = json.load(f)
                    if 'watch_pool' in pool:
                        stock_list = list(set(stock_list + pool['watch_pool']))
                        sys_logger.info(f"✅ 合并 watch_pool，总监控 {len(stock_list)} 只")
            except: pass

        sys_logger.info(f"正在获取 {len(stock_list)} 只标的行情...")
        
        # [修改点] 使用 Safe 版本获取实时行情
        realtime_data = get_realtime_data_safe(stock_list)
        
        if not realtime_data:
            sys_logger.error("❌ 3次重试后仍无法获取实时行情，任务中止")
            return

        sent_signals = load_sent_signals()

        # [回归单线程] 逐个分析，确保日志顺序
        for code, info in realtime_data.items():
            name = info['name']
            # 简单过滤：如果停牌或无成交量，跳过
            if info['vol'] == 0 or info['price'] == 0: continue
                
            sys_logger.info(f"分析: {name} ({code})...")
            
            # 1. 获取K线 (内部自带换IP机制)
            kline_df = get_kline_safe(code)
            
            if kline_df is None or kline_df.empty:
                sys_logger.error(f"❌ {name} 彻底失败，跳过")
                continue

            # 2. 数据缝合
            today_str = datetime.now().strftime('%Y-%m-%d')
            last_date = str(kline_df.iloc[-1]['date'])[:10] if 'date' in kline_df.columns else ''
            
            if last_date != today_str and info['vol'] > 0:
                new_row = pd.DataFrame({
                    'date': [today_str],
                    'open': [info['open']],
                    'close': [info['price']],
                    'high': [info['high']],
                    'low': [info['low']],
                    'volume': [info['vol']],
                    'pct_chg': [info['pct']],
                    'turnover': [info.get('turnover', 0)]
                })
                kline_df = pd.concat([kline_df, new_row], ignore_index=True)
                sys_logger.info(f"   └── 已缝合今日实时数据 (现价 {info['price']})")

            latest_news = get_stock_news(code, top_n=10)
            if latest_news:
                sys_logger.info(f"   └── 抓取到 {len(latest_news)} 条新闻")

            indicators = compute_indicators(kline_df)
            patterns = detect_candlestick_patterns(kline_df)
            
            # 3. DeepSeek 分析 (强制直连)
            time.sleep(0.5)
            with no_proxy():
                analysis = analyze_stock_technical(
                    code, name, kline_df,
                    news_list=latest_news,
                    indicators=indicators,
                    patterns=patterns
                )
            
            if not analysis: continue

            signal = analysis.get('signal', 'HOLD')
            confidence = analysis.get('confidence', 0)
            reason = analysis.get('reason', '无理由')
            
            sys_logger.info(f"   └── AI分析: {signal} | 信心: {confidence} | {reason}")

            last_signal = sent_signals.get(code)
            # 门槛设定为 70 (激进模式下 AI 很容易给 85-95)
            if signal in ['BUY', 'SELL'] and confidence >= 70:
                if last_signal != signal:
                    title = f"🚀 {signal} 信号: {name} ({code})"
                    
                    # [完全一致的 HTML 格式]
                    content = f"""
                    <b>代码</b>: {code}<br>
                    <b>名称</b>: {name}<br>
                    <b>现价</b>: {info['price']} ({info['pct']}%)<br>
                    <b>量比</b>: {info.get('lb', 'N/A')}<br>
                    <b>信心</b>: {confidence}/100<br>
                    <b>AI分析</b>: {reason}<br>
                    <hr>
                    <i>DeepSniper 自动生成 @ {datetime.now().strftime('%H:%M')}</i>
                    """
                    
                    if send_wechat_message(title, content):
                        save_signal(code, signal)
                        sys_logger.info(f"✅ 推送成功")
                    else:
                        sys_logger.warning(f"❌ 推送失败")
                else:
                    sys_logger.info(f"🔄 信号重复 ({last_signal})，今日已发过")

    except Exception as e:
        sys_logger.error(f"❌ 任务异常: {e}")

if __name__ == "__main__":
    sys_logger.info(">>> 循环模式启动 <<<")
    while True:
        now = datetime.now()
        # 保持你原来的逻辑：周一到周五 9点到15点运行
        if now.weekday() < 5 and (9 <= now.hour < 15):
            run_deep_sniper_analysis()
            time.sleep(900)
        else:
            time.sleep(3600)