import os
import sys
import time
from datetime import datetime, time as d_time
from contextlib import contextmanager

# --- 1. 环境路径设置 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.append(PROJECT_ROOT)

from utils.logger import sys_logger
from update_stock_pool import update_stock_pool_once, load_config, fetch_and_set_proxy
# [修改点] 只导入主函数，不导入 unset_proxy
from main_quant import run_deep_sniper_analysis

# --- 2. 核心工具函数 (本地定义，不依赖 main_quant) ---

def unset_proxy():
    """彻底清除系统代理，确保推送服务直连"""
    keys = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
    for key in keys:
        if key in os.environ:
            del os.environ[key]

@contextmanager
def proxy_scope(conf):
    """
    代理上下文管理器：确保只在抓取数据时开启代理，
    退出代码块（无论是否报错）都会自动执行 unset_proxy。
    """
    try:
        fetch_and_set_proxy(conf)
        yield
    finally:
        unset_proxy()

def get_market_status():
    """
    更精细的市场时间片状态机
    """
    now = datetime.now()
    if now.weekday() >= 5:
        return "WEEKEND", 3600  # 周末每小时检查一次

    curr_t = now.time()
    
    # 1. 早盘集合竞价前准备 (09:00 - 09:30)
    if d_time(9, 0) <= curr_t < d_time(9, 30):
        return "PRE_MARKET", 300  # 每5分钟更新一次股票池
    
    # 2. 上午交易时段 (09:30 - 11:31)
    if d_time(9, 30) <= curr_t < d_time(11, 31):
        return "TRADING", None    # 使用 config 中的间隔
    
    # 3. 午间休盘 (11:31 - 12:59)
    if d_time(11, 31) <= curr_t < d_time(12, 59):
        return "LUNCH_BREAK", 600 # 每10分钟检查一次
    
    # 4. 下午交易时段 (13:00 - 15:05)
    if d_time(13, 0) <= curr_t < d_time(15, 5):
        return "TRADING", None
    
    # 5. 收盘后总结 (15:05 - 15:30)
    if d_time(15, 5) <= curr_t < d_time(15, 30):
        return "POST_MARKET", 1800 # 跑完进入总结
        
    return "IDLE", 900 

# --- 3. 主调度循环 ---

def run_master_loop():
    sys_logger.info("========================================")
    sys_logger.info("🚀 DeepSniper 智能交易守护进程启动")
    sys_logger.info(f"📍 项目根目录: {PROJECT_ROOT}")
    sys_logger.info("========================================")
    
    while True:
        try:
            now = datetime.now()
            status, wait_seconds = get_market_status()
            conf = load_config()
            
            # 获取配置的扫描间隔
            config_interval = conf.get('strategy_params', {}).get('SCAN_INTERVAL_MINUTES', 15) * 60
            loop_wait = wait_seconds if wait_seconds else config_interval

            if status in ["PRE_MARKET", "TRADING", "POST_MARKET"]:
                sys_logger.info(f"🔔 [状态: {status}] 开始执行任务流...")
                
                # Step A: 数据更新 (Proxy ON)
                with proxy_scope(conf):
                    sys_logger.info(f"   └── (1/2) 正在更新股票池与行情数据...")
                    try:
                        update_stock_pool_once(conf)
                    except Exception as e:
                        sys_logger.error(f"❌ 更新股票池失败: {e}")
                
                # Step B: 深度分析与信号推送 (Proxy OFF)
                # 退出 proxy_scope 后，代理已被清理
                sys_logger.info(f"   └── (2/2) 正在执行 DeepSniper 深度量化分析 (推送直连)...")
                
                # 双重保险：再次清理，确保不影响 DeepSeek 和 微信推送
                unset_proxy()
                run_deep_sniper_analysis()
                
                if status == "POST_MARKET":
                    sys_logger.info("📊 今日交易时段结束，完成最后一次同步。")

                sys_logger.info(f"✅ 本轮任务完成，系统将休眠 {int(loop_wait/60)} 分钟。")
            
            else:
                sys_logger.info(f"💤 [状态: {status}] 非核心交易时段，系统待机中...")
            
        except KeyboardInterrupt:
            sys_logger.warning("🛑 用户手动停止脚本")
            sys.exit(0)
        except Exception as e:
            sys_logger.error(f"💥 调度器运行异常: {str(e)}", exc_info=True)
            unset_proxy()
            loop_wait = 60 # 发生异常等待1分钟

        time.sleep(loop_wait)

if __name__ == "__main__":
    run_master_loop()