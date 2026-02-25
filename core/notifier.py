import os
from datetime import datetime

class Notifier:
    def __init__(self):
        self.report_dir = "reports"
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir)

    def generate_report(self, stock_name, strategy_result, ai_result, news_summary):
        """
        生成决策日报
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H:%M")
        
        # 判定最终建议
        final_decision = "👀 观望"
        if strategy_result['signal'] == "SELL":
            final_decision = "🏃‍♂️ 快跑 (技术面破位)"
        elif strategy_result['signal'] == "BUY" and ai_result['score'] > 0:
            final_decision = "🚀 All-in 买入 (共振)"
        elif strategy_result['signal'] == "BUY" and ai_result['score'] < 0:
            final_decision = "⚠️ 风险警示 (技术买入但AI看空)"

        # Markdown 模板
        content = f"""
# 📉 DeepSniper 决策日报 [{date_str} {time_str}]

## 1. 核心决断
# **{final_decision}**

---

## 2. 实时盘面 ({stock_name})
* **最新价格**: {strategy_result['price']} (涨跌: {strategy_result['change_pct']}%)
* **生命线 (MA5)**: {strategy_result['ma5']}
* **技术状态**: {strategy_result['signal']}
* **判断理由**: {strategy_result['reasons']}

---

## 3. AI 大脑分析
* **情感打分**: {ai_result.get('score', 0)} / 1.0
* **核心观点**: {ai_result.get('reason', '无')}
* **操作建议**: {ai_result.get('action_advice', '无')}

---

## 4. 关键情报
{news_summary}
        """
        
        # 保存文件
        filename = f"{self.report_dir}/{date_str}_{stock_name}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content.strip())
            
        print(f"📝 报告已生成: {filename}")
        return content

notifier = Notifier()