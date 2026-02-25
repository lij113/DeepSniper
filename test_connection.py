from core.llm_client import llm_client
from config.prompts import Prompts

def test_brain():
    print(">>> 正在向 DeepSeek 发送测试指令...")
    
    # 模拟一条新闻
    fake_news = "OPEC+ 宣布为了稳定油价，将推迟原定的增产计划至明年底。但美股石油板块昨夜高开低走。"
    
    # 调用
    result = llm_client.get_analysis(
        Prompts.SENTIMENT_ANALYSIS,
        persona=Prompts.TRADER_PERSONA,
        stock_name="中曼石油",
        news_content=fake_news
    )
    
    print("\n" + "="*30)
    print("🤖 大脑反馈结果:")
    print(f"情感打分: {result.get('score')}")
    print(f"核心理由: {result.get('reason')}")
    print(f"操作建议: {result.get('action_advice')}")
    print("="*30)

if __name__ == "__main__":
    test_brain()