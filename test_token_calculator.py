#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token计算器测试和使用示例
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from token_calculator import TokenCalculator, ModelType
import json
import time


def test_basic_token_calculation():
    """测试基本token计算功能"""
    print("="*50)
    print("测试1: 基本Token计算")
    print("="*50)
    
    calculator = TokenCalculator()
    
    # 测试文本
    test_texts = [
        "你好",
        "Hello, world!",
        "这是一个测试文本，用于验证token计算功能。",
        "股票代码603619当前价格为36.50元，成交量100万手。",
        """
        请分析以下技术指标：
        - MA5: 35.20
        - MA20: 34.80
        - RSI: 65.3
        - MACD: 金叉形成
        
        建议操作：买入
        止损位：35.00
        """,
        """{"analysis": {"score": 85.5, "confidence": "high", "signals": ["buy", "hold"]}, "timestamp": "2024-01-15T10:30:00Z"}"""
    ]
    
    for i, text in enumerate(test_texts):
        print(f"\n文本 {i+1}: {text[:30]}...")
        
        # 测试不同模型的token计算
        models = ["deepseek-reasoner", "gpt-4o", "gpt-3.5-turbo", "claude-3-sonnet"]
        
        for model in models:
            tokens = calculator.count_tokens(text, model)
            char_count = len(text)
            ratio = tokens / char_count if char_count > 0 else 0
            
            print(f"  {model}: {tokens} tokens (比率: {ratio:.3f})")


def test_text_efficiency_analysis():
    """测试文本效率分析"""
    print("\n" + "="*50)
    print("测试2: 文本效率分析")
    print("="*50)
    
    calculator = TokenCalculator()
    
    # 不同类型的测试文本
    test_cases = [
        {
            "name": "简洁文本",
            "text": "买入。"
        },
        {
            "name": "中等长度文本",
            "text": "基于技术分析，该股票出现金叉信号，建议买入。止损位设置在35.00。"
        },
        {
            "name": "详细分析文本",
            "text": """
            股票代码603619技术分析报告：
            
            1. 技术指标分析：
               - MA5: 35.20 (生命线)
               - MA20: 34.80 (趋势线)
               - RSI: 65.3 (强势区域)
               - MACD: 金叉形成，买入信号强烈
               - 成交量: 100万手，放量上涨
            
            2. 市场环境：
               - 大盘处于上涨趋势
               - 行业板块表现活跃
               - 资金流入明显
            
            3. 操作建议：
               - 建议买入
               - 止损位：35.00
               - 目标位：38.50
               - 持仓周期：1-2周
            
            4. 风险提示：
               - 注意大盘波动风险
               - 设置好止损位
               - 控制仓位风险
            """
        },
        {
            "name": "JSON格式数据",
            "text": """{"stock": "603619", "price": 36.50, "analysis": {"score": 85.5, "signals": ["buy"], "confidence": "high"}, "timestamp": "2024-01-15T10:30:00Z"}"""
        }
    ]
    
    for case in test_cases:
        print(f"\n{case['name']}:")
        analysis = calculator.analyze_text_efficiency(case['text'], "deepseek-reasoner")
        
        if analysis:
            print(f"  字符数: {analysis['text_length']}")
            print(f"  Token数: {analysis['token_count']}")
            print(f"  Token/字符比率: {analysis['token_char_ratio']:.3f}")
            print(f"  效率评级: {analysis['efficiency_rating']}")
            print(f"  估算成本: ${analysis['estimated_cost']:.6f}")
        else:
            print("  分析失败")


def test_batch_analysis():
    """测试批量分析功能"""
    print("\n" + "="*50)
    print("测试3: 批量分析功能")
    print("="*50)
    
    calculator = TokenCalculator()
    
    # 模拟一批股票分析文本
    stock_texts = [
        "603619: MA5金叉，建议买入，止损35.00",
        "000858: 技术指标走弱，建议观望",
        "600519: 价值投资，长期持有",
        "000002: 地产龙头，政策利好，建议关注",
        "300750: 创业板龙头，成长性好，适合长期投资"
    ]
    
    print("批量分析结果:")
    results = calculator.batch_analyze_texts(stock_texts, "deepseek-reasoner")
    
    for result in results:
        if 'error' not in result:
            print(f"  文本 {result['text_index']+1}: {result['token_count']} tokens, {result['efficiency_rating']}")
            print(f"    预览: {result['text_preview']}")
        else:
            print(f"  文本 {result['text_index']+1}: 分析失败 - {result['error']}")


def test_api_call_recording():
    """测试API调用记录功能"""
    print("\n" + "="*50)
    print("测试4: API调用记录功能")
    print("="*50)
    
    calculator = TokenCalculator()
    
    # 模拟API调用
    api_calls = [
        {
            "model": "deepseek-reasoner",
            "prompt": "分析股票603619的技术面",
            "response": "该股票技术面良好，建议买入",
            "success": True
        },
        {
            "model": "gpt-4o",
            "prompt": "总结今天的市场行情",
            "response": "市场整体表现良好，科技股领涨",
            "success": True
        },
        {
            "model": "deepseek-reasoner",
            "prompt": "分析股票000858的投资价值",
            "response": "",  # 模拟失败情况
            "success": False,
            "error": "API连接超时"
        }
    ]
    
    for call in api_calls:
        input_tokens = calculator.count_tokens(call["prompt"], call["model"])
        output_tokens = calculator.count_tokens(call["response"], call["model"]) if call["success"] else 0
        
        calculator.record_api_call(
            model=call["model"],
            prompt=call["prompt"],
            response=call["response"],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            success=call["success"],
            error_message=call.get("error")
        )
        
        print(f"记录API调用: {call['model']}")
        print(f"  输入: {input_tokens} tokens")
        print(f"  输出: {output_tokens} tokens")
        print(f"  状态: {'成功' if call['success'] else '失败'}")
        if not call['success']:
            print(f"  错误: {call['error']}")
    
    # 打印使用报告
    print("\n使用报告:")
    calculator.print_usage_report()


def test_cost_calculation():
    """测试成本计算功能"""
    print("\n" + "="*50)
    print("测试5: 成本计算功能")
    print("="*50)
    
    calculator = TokenCalculator()
    
    # 测试不同模型的成本
    test_scenarios = [
        {
            "model": "deepseek-reasoner",
            "input_tokens": 1000,
            "output_tokens": 500
        },
        {
            "model": "gpt-4o",
            "input_tokens": 1000,
            "output_tokens": 500
        },
        {
            "model": "gpt-4o-mini",
            "input_tokens": 1000,
            "output_tokens": 500
        },
        {
            "model": "gpt-3.5-turbo",
            "input_tokens": 1000,
            "output_tokens": 500
        },
        {
            "model": "claude-3-sonnet",
            "input_tokens": 1000,
            "output_tokens": 500
        }
    ]
    
    print("不同模型的成本对比:")
    print("-"*60)
    print(f"{'模型':<20} {'输入Token':<10} {'输出Token':<10} {'成本($)':<12}")
    print("-"*60)
    
    total_cost = 0
    for scenario in test_scenarios:
        cost = calculator.calculate_api_call_cost(
            scenario["model"],
            scenario["input_tokens"],
            scenario["output_tokens"]
        )
        total_cost += cost
        
        print(f"{scenario['model']:<20} {scenario['input_tokens']:<10} {scenario['output_tokens']:<10} {cost:<12.4f}")
    
    print("-"*60)
    print(f"{'总计':<20} {'':<10} {'':<10} {total_cost:<12.4f}")


def test_model_pricing():
    """测试模型定价信息"""
    print("\n" + "="*50)
    print("测试6: 模型定价信息")
    print("="*50)
    
    calculator = TokenCalculator()
    
    print("支持的模型及其定价:")
    print("-"*80)
    print(f"{'模型':<25} {'输入价格($/1K)':<15} {'输出价格($/1K)':<15}")
    print("-"*80)
    
    for model_type, pricing in calculator.model_pricing.items():
        print(f"{model_type.value:<25} {pricing['input']:<15.2f} {pricing['output']:<15.2f}")
    
    print("-"*80)


def test_export_functionality():
    """测试导出功能"""
    print("\n" + "="*50)
    print("测试7: 导出功能")
    print("="*50)
    
    calculator = TokenCalculator()
    
    # 先添加一些记录
    test_text = "这是一个测试文本，用于验证导出功能。"
    input_tokens = calculator.count_tokens(test_text, "deepseek-reasoner")
    output_tokens = input_tokens // 2
    
    calculator.record_api_call(
        model="deepseek-reasoner",
        prompt=test_text,
        response="这是测试响应。",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        success=True
    )
    
    # 导出报告
    output_path = "test_token_report.json"
    calculator.export_usage_report(output_path)
    
    # 验证文件是否创建
    if os.path.exists(output_path):
        print(f"✓ 报告已成功导出到: {output_path}")
        
        # 读取并显示报告内容
        with open(output_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        print("\n报告摘要:")
        print(f"总调用次数: {report['summary']['total_calls']}")
        print(f"总成本: ${report['summary']['total_cost']:.4f}")
        print(f"总Token数: {report['summary']['total_tokens']}")
        
    else:
        print("✗ 报告导出失败")


def test_integration_with_existing_system():
    """测试与现有系统集成"""
    print("\n" + "="*50)
    print("测试8: 与现有系统集成")
    print("="*50)
    
    # 模拟从现有系统获取的数据
    from config.config import Config
    
    calculator = TokenCalculator()
    
    # 读取配置文件中的模型设置
    config = calculator.config
    llm_config = config.get("llm", {})
    
    print("当前系统配置:")
    print(f"模型名称: {llm_config.get('model_name', '未设置')}")
    print(f"最大Token数: {llm_config.get('max_tokens', '未设置')}")
    print(f"基础URL: {llm_config.get('base_url', '未设置')}")
    
    # 模拟系统中的提示模板
    prompt_templates = {
        "股票分析": "请分析股票{symbol}的技术面，当前价格{price}，成交量{volume}。",
        "市场总结": "总结今天的市场行情，重点关注{sectors}板块的表现。",
        "风险评估": "评估股票{symbol}的投资风险，包括技术面、基本面和市场环境。"
    }
    
    print("\n分析系统提示模板的Token使用情况:")
    print("-"*60)
    
    for template_name, template in prompt_templates.items():
        # 模拟参数填充
        if template_name == "股票分析":
            filled_prompt = template.format(symbol="603619", price="36.50", volume="100万手")
        elif template_name == "市场总结":
            filled_prompt = template.format(sectors="科技、金融、消费")
        else:  # 风险评估
            filled_prompt = template.format(symbol="603619")
        
        input_tokens = calculator.count_tokens(filled_prompt, "deepseek-reasoner")
        estimated_output_tokens = max(1, int(input_tokens * 0.3))
        cost = calculator.calculate_api_call_cost("deepseek-reasoner", input_tokens, estimated_output_tokens)
        
        print(f"{template_name}:")
        print(f"  提示长度: {len(filled_prompt)} 字符")
        print(f"  输入Token: {input_tokens}")
        print(f"  估算输出Token: {estimated_output_tokens}")
        print(f"  估算成本: ${cost:.4f}")
        print()


def main():
    """主测试函数"""
    print("Token计算器测试套件")
    print("="*60)
    
    try:
        # 运行所有测试
        test_basic_token_calculation()
        test_text_efficiency_analysis()
        test_batch_analysis()
        test_api_call_recording()
        test_cost_calculation()
        test_model_pricing()
        test_export_functionality()
        test_integration_with_existing_system()
        
        print("\n" + "="*60)
        print("所有测试完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()