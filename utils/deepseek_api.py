import os
import sys
import json
import time
import requests
from typing import Optional, Dict, Any, List

# --- 1. 环境路径设置 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.append(PROJECT_ROOT)

from utils.logger import sys_logger

# --- 2. 常量与配置加载 ---
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config', 'config.json')

def load_deepseek_config() -> tuple[Optional[str], Optional[str], Optional[str], Optional[dict]]:
    if not os.path.exists(CONFIG_PATH):
        sys_logger.error(f"❌ 配置文件未找到: {CONFIG_PATH}")
        return None, None, None, {}

    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            conf = json.load(f)
            ds_conf = conf.get('deepseek', {})
            api_key = ds_conf.get('API_KEY')
            base_url = ds_conf.get('BASE_URL', 'https://api.deepseek.com')
            model = ds_conf.get('MODEL', 'deepseek-chat')
            extra = {
                'temperature': ds_conf.get('temperature', 0.3),  # 温度略微提高到0.3，更灵活
                'max_tokens': ds_conf.get('max_tokens', 1024),
                'timeout': ds_conf.get('request_timeout', 30),
                'retries': ds_conf.get('retries', 3)
            }
            return api_key, base_url, model, extra
    except Exception as e:
        sys_logger.error(f"❌ 配置读取异常: {e}")
        return None, None, None, {}

# --- 3. 核心分析函数 ---
def analyze_stock_technical(
    stock_code: str,
    stock_name: str,
    kline_data: Any,
    news_list: Optional[List[str]] = None,
    indicators: Optional[Dict[str, Any]] = None,
    patterns: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    api_key, base_url, model, extra = load_deepseek_config()
    if not api_key:
        return None

    indicators = indicators or {}
    news_list = news_list or []
    patterns = patterns or []

    # 1. 数据预处理
    if hasattr(kline_data, 'tail'):
        cols = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '换手率']
        available_cols = [c for c in cols if c in kline_data.columns]
        k_str = kline_data[available_cols].tail(10).to_string(index=False, header=True)
    else:
        k_str = str(kline_data)[-1000:]

    news_str = "\n".join(news_list[:10]) if news_list else "无重大利好催化"
    patterns_str = "、".join(patterns) if patterns else "无明显形态"

    # 关键指标
    vol_ratio = indicators.get('vol_ratio', 1.0)
    adx = indicators.get('adx', 0)
    rsi = indicators.get('rsi', 50)
    recent_return = indicators.get('recent_return', 0)  # 近期收益

    # === System Prompt: 放宽为人设更均衡的短线操盘手 ===
    system_prompt = (
        "你是一名经验丰富的短线操盘手，风格偏趋势与活跃结合，既能抓住龙头爆发，也接受温和放量趋势机会。\n"
        "核心原则：风险第一，胜率优先，但不完全放弃合理机会。\n"
        "你的风格：\n"
        "1. 进攻性极强：你深知短线本质是‘情绪+资金’，宁可错过不可做错，但在行情启动初期你必须果断出击。\n"
        "2. 拥抱分歧：你擅长在分歧中寻找‘弱转强’、‘反包板’和‘首板突破’的机会。\n"
        "3. 极致审美：你厌恶跟风票，只看龙头和高辨识度标的。你允许技术指标有微瑕，只要情绪和量能够火热。\n"
        "4. 果断决策：拒绝模棱两可。如果机会达到 70% 的成功率，你就会视为必争之地。\n"
        "注意：你现在的输出将直接决定千万级资金的去向，请展现你的专业果敢。"
    )

    # === User Prompt: 放宽标准 + 更平衡审视 ===
    user_prompt = f"""
【标的】：{stock_name} ({stock_code})

【近期K线（最近10日）】
{k_str}

【核心量化指标】
{json.dumps(indicators, ensure_ascii=False, indent=2)}

【形态与消息】
- K线形态: {patterns_str}
- 近期新闻: {news_str}

【审核清单（逐项分析）】
1. 量能：量比 {vol_ratio:.2f} 是否活跃？>3强势，1.5-3温和放量可接受，<1.2警惕缩量。
2. 趋势强度：ADX {adx:.1f} 是否>25（趋势确立）？>35加分，<20减分。
3. RSI {rsi:.1f} 是否50-85强势区？>85警惕超买。
4. 是否有弱转强/反包/突破确认？或至少站稳均线+温和上涨？
5. 题材催化：是否有实质利好？板块是否有共振？无催化但技术健康也可部分认可。
6. 近期表现：10日涨幅 {recent_return:.1%} 是否健康上攻？

【评分标准（平衡短线）】
- 0-50分：弱势/杂毛 → IGNORE（无机会，回避）
- 51-70分：潜在机会 → HOLD（观察或轻仓）
- 71-100分：强势机会 → BUY（可操作，信心越高越优先）

【输出严格JSON】
{{
    "signal": "BUY" | "HOLD" | "IGNORE",
    "confidence": 0-100（BUY需>65，HOLD 40-75，IGNORE <50）,
    "reason": "游资风格总结，限40字",
    "risk_points": ["风险1", "风险2"]（2-3个主要风险，即使BUY也要指出）,
    "short_report": "简洁分析+操作建议，限100字"
}}
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": extra.get('temperature', 0.3),  # 温度提高到0.3，更灵活判断
        "max_tokens": extra.get('max_tokens', 1024),
        "response_format": {"type": "json_object"}
    }

    url = f"{base_url.rstrip('/')}/chat/completions"
    timeout = extra.get('timeout', 30)
    retries = extra.get('retries', 3)

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                raw_content = response.json()['choices'][0]['message']['content']
                
                if "```" in raw_content:
                    raw_content = raw_content.split("```json")[-1].split("```")[0].strip()
                
                result = json.loads(raw_content)
                
                if result.get('signal') in ['SELL', 'NO']:
                    result['signal'] = 'IGNORE'
                
                sys_logger.info(f"✅ DeepSeek 分析成功 [{stock_code}]：{result['signal']} (信心: {result['confidence']})")
                return result
            
            else:
                sys_logger.warning(f"⚠️ API 返回错误 (尝试 {attempt}): {response.status_code} {response.text[:200]}")
        
        except json.JSONDecodeError as e:
            sys_logger.warning(f"⚠️ JSON 解析失败 (尝试 {attempt}): {e} | 原始: {raw_content[:300] if 'raw_content' in locals() else 'N/A'}")
        except Exception as e:
            sys_logger.warning(f"⚠️ 请求异常 (尝试 {attempt}): {e}")
        
        if attempt < retries:
            time.sleep(2 ** attempt)

    sys_logger.error(f"❌ DeepSeek 分析彻底失败 [{stock_code}]")
    return None

# --- 4. 测试入口 ---
if __name__ == "__main__":
    sys_logger.info(">>> DeepSeek API 测试启动 <<<")
    
    # 测试案例1：温和趋势票（之前会被判杂毛，现在应给HOLD）
    indicators_mild = {"vol_ratio": 1.8, "adx": 28, "rsi": 68, "recent_return": 0.12}
    res1 = analyze_stock_technical(
        stock_code="000001",
        stock_name="温和趋势股",
        kline_data="模拟K线数据...",
        indicators=indicators_mild,
        patterns=["站上均线", "温和放量"]
    )
    sys_logger.info("\n[测试1: 温和趋势]\n" + json.dumps(res1, indent=2, ensure_ascii=False))
    
    # 测试案例2：强势龙头
    indicators_strong = {"vol_ratio": 3.5, "adx": 45, "rsi": 80, "recent_return": 0.25}
    res2 = analyze_stock_technical(
        stock_code="000002",
        stock_name="强势龙头",
        kline_data="模拟K线数据...",
        indicators=indicators_strong,
        patterns=["弱转强", "反包", "量比放大"],
        news_list=["重大政策利好", "业绩大幅预增"]
    )
    sys_logger.info("\n[测试2: 强势龙头]\n" + json.dumps(res2, indent=2, ensure_ascii=False))