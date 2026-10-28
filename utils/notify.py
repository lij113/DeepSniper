import requests
import json
import os
from datetime import datetime

# 加载主配置（所有模块都会用这个方式加载）
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"配置文件缺失: {CONFIG_PATH}")
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

config = load_config()
APP_TOKEN = config['wxpusher']['APP_TOKEN']
UID = config['wxpusher']['UID']

def send_wechat_message(title: str, content: str, uids: list = None):
    """
    发送微信通知（WxPusher）
    :param title: 标题（通知栏显示）
    :param content: HTML内容
    :param uids: UID列表，默认用配置里的单个UID
    """
    if not APP_TOKEN or not UID:
        print("【错误】WxPusher 配置不完整，无法发送通知")
        return False
    
    target_uids = uids or [UID]
    
    url = 'https://wxpusher.zjiecode.com/api/send/message'
    data = {
        "appToken": APP_TOKEN,
        "content": f"<b>{title}</b><br><br>{content}",
        "summary": title,
        "contentType": 2,  # HTML
        "uids": target_uids
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        if result.get('success'):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 微信通知发送成功: {title}")
            return True
        else:
            print(f"【通知失败】{result}")
            return False
    except Exception as e:
        print(f"【通知异常】{e}")
        return False

# 测试用（直接运行这个文件时执行）
if __name__ == '__main__':
    test_content = """
    utils/notify.py 测试成功！<br><br>
    时间：{time}<br>
    通知模块正常工作，带铃声振动🚀
    """.format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    send_wechat_message("DeepSniper 通知模块测试", test_content)