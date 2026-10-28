import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 1. 动态定位 logs 目录 (在当前文件的上级目录的 logs 文件夹)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def setup_logger(name="DeepSniper"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 避免重复添加 handler (防止日志打印两遍)
    if logger.handlers:
        return logger

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # A. 文件输出 (run.log)
    file_path = os.path.join(LOG_DIR, "run.log")
    file_handler = RotatingFileHandler(
        file_path, 
        maxBytes=10*1024*1024, # 10MB 切割
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # B. 控制台输出 (屏幕显示)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# ==========================================
# ⚠️ 关键修复：必须在这里初始化并赋值给 sys_logger
# 这样其他文件才能 from utils.logger import sys_logger
# ==========================================
sys_logger = setup_logger()