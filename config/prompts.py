class Prompts:
    TRADER_PERSONA = "" # R1 不需要这里单独设人设，直接写在下面

    # 针对 R1 的深度推理模板
    SENTIMENT_ANALYSIS = """
    你是一个负责几十亿资金的量化基金经理。现在需要对股票【{stock_name}】做出最终交易决策。
    
    【市场情报】：
    1. 盘面表现：{technical_signal} (涨跌幅: {change_pct}%, 现价: {price})
    2. 新闻舆情：
    {news_content}
    
    【请进行深度推理 (Chain of Thought)】：
    请在内心思考以下问题：
    - 新闻是真利好还是配合出货的“小作文”？
    - 技术面和消息面是否背离？（例如：利好发布但股价不涨反跌 -> 也就是“见光死”）
    - 盈亏比是否划算？
    
    【最终输出】：
    推理完成后，请严格只输出一个 JSON 格式结果（不要包含任何其他文字）：
    {{
        "score": float,     // -1.0 ~ 1.0 (必须精确)
        "reason": "string", // 一针见血的理由 (20字内)
        "action_advice": "string" // 明确指令：买入/止损/观望
    }}
    """