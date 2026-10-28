import json
import os
import efinance as ef  # 你的其他引用

def load_config_and_set_proxy(config_path='/root/my_workspace/DeepSniper/config/config.json'):
    """加载配置并自动设置系统代理"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件 {config_path} 未找到")
        
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 1. 设置网络代理 (核心步骤)
    if 'network' in config:
        # 设置 http_proxy 和 https_proxy 环境变量
        # requests 库会自动读取这两个变量
        os.environ['http_proxy'] = config['network'].get('http_proxy', '')
        os.environ['https_proxy'] = config['network'].get('https_proxy', '')
        
        print(f"🌐 代理已配置: {os.environ['http_proxy']}")
    else:
        print("⚠️ 警告: 配置文件中未发现 network 代理设置，可能会导致 IP 被封")

    return config

# ================= 使用示例 =================

# 1. 程序启动时加载
config = load_config_and_set_proxy()

# 2. 这里的 config 同时也包含了 strategy_params 等参数，可以直接用
scan_interval = config['strategy_params']['SCAN_INTERVAL_MINUTES']
print(f"策略扫描间隔: {scan_interval} 分钟")

# 3. 现在调用 efinance 就会自动走代理了
# df = ef.stock.get_realtime_quotes()