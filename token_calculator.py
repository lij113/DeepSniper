#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token计算器 - 计算各种LLM模型的token用量
支持DeepSeek、GPT等多种模型的token计算
"""

import re
import json
import yaml
import time
import logging
from typing import Dict, List, Union, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
import tiktoken
import openai

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ModelType(Enum):
    """支持的模型类型"""
    DEEPSEEK_REASONER = "deepseek-reasoner"
    DEEPSEEK_CHAT = "deepseek-chat"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_3_5_TURBO_16K = "gpt-3.5-turbo-16k"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_OPUS = "claude-3-opus"


@dataclass
class TokenUsage:
    """token使用情况数据类"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    
    def __post_init__(self):
        self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class APICallRecord:
    """API调用记录"""
    timestamp: float
    model: str
    prompt: str
    response: str
    token_usage: TokenUsage
    cost: float
    success: bool = True
    error_message: Optional[str] = None


class TokenCalculator:
    """Token计算器主类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化Token计算器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.api_records: List[APICallRecord] = []
        self.token_stats = defaultdict(lambda: defaultdict(int))
        
        # 初始化OpenAI客户端（用于token计算）
        self._init_openai_client()
        
        # 模型定价信息（每1K tokens的价格，单位：美元）
        self.model_pricing = {
            ModelType.DEEPSEEK_REASONER: {"input": 0.14, "output": 0.28},
            ModelType.DEEPSEEK_CHAT: {"input": 0.14, "output": 0.28},
            ModelType.GPT_4O: {"input": 2.5, "output": 10.0},
            ModelType.GPT_4O_MINI: {"input": 0.15, "output": 0.60},
            ModelType.GPT_4_TURBO: {"input": 3.0, "output": 6.0},
            ModelType.GPT_4: {"input": 3.0, "output": 6.0},
            ModelType.GPT_3_5_TURBO: {"input": 0.5, "output": 1.5},
            ModelType.GPT_3_5_TURBO_16K: {"input": 3.0, "output": 4.0},
            ModelType.CLAUDE_3_HAIKU: {"input": 0.25, "output": 1.25},
            ModelType.CLAUDE_3_SONNET: {"input": 3.0, "output": 15.0},
            ModelType.CLAUDE_3_OPUS: {"input": 15.0, "output": 75.0},
        }
        
        logger.info("Token计算器初始化完成")
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"配置文件 {self.config_path} 不存在，使用默认配置")
            return {"llm": {"model_name": "deepseek-reasoner"}}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {"llm": {"model_name": "deepseek-reasoner"}}
    
    def _init_openai_client(self):
        """初始化OpenAI客户端"""
        try:
            # 从配置文件和环境变量加载API配置
            api_key = self.config.get("llm", {}).get("api_key") or os.getenv("OPENAI_API_KEY")
            base_url = self.config.get("llm", {}).get("base_url") or "https://api.openai.com/v1"
            
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key, base_url=base_url)
                logger.info("OpenAI客户端初始化成功")
            else:
                self.openai_client = None
                logger.warning("未找到OpenAI API密钥，部分功能可能受限")
        except Exception as e:
            logger.error(f"初始化OpenAI客户端失败: {e}")
            self.openai_client = None
    
    def get_encoding(self, model: str) -> tiktoken.Encoding:
        """
        获取模型的编码器
        
        Args:
            model: 模型名称
            
        Returns:
            编码器对象
        """
        model_mapping = {
            "gpt-4": "cl100k_base",
            "gpt-4-turbo": "cl100k_base",
            "gpt-4o": "cl100k_base",
            "gpt-4o-mini": "cl100k_base",
            "gpt-3.5-turbo": "cl100k_base",
            "gpt-3.5-turbo-16k": "cl100k_base",
            "deepseek-reasoner": "cl100k_base",
            "deepseek-chat": "cl100k_base",
        }
        
        encoding_name = model_mapping.get(model, "cl100k_base")
        return tiktoken.get_encoding(encoding_name)
    
    def count_tokens(self, text: str, model: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 要计算的文本
            model: 模型名称
            
        Returns:
            token数量
        """
        if not text:
            return 0
        
        try:
            encoding = self.get_encoding(model)
            tokens = encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.error(f"计算token失败: {e}")
            return 0
    
    def count_tokens_messages(self, messages: List[Dict[str, str]], model: str) -> Tuple[int, int]:
        """
        计算消息列表的输入和输出token数量
        
        Args:
            messages: 消息列表，格式如 [{"role": "user", "content": "你好"}]
            model: 模型名称
            
        Returns:
            (输入token数量, 输出token数量估算)
        """
        if not messages:
            return 0, 0
        
        try:
            # 计算输入token
            input_text = ""
            for msg in messages:
                if msg.get("role") and msg.get("content"):
                    input_text += f"{msg['role']}: {msg['content']}\n"
            
            input_tokens = self.count_tokens(input_text, model)
            
            # 估算输出token（通常为输入的1/4到1/3）
            output_tokens = max(1, int(input_tokens * 0.25))
            
            return input_tokens, output_tokens
        except Exception as e:
            logger.error(f"计算消息token失败: {e}")
            return 0, 0
    
    def calculate_api_call_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        计算API调用的成本
        
        Args:
            model: 模型名称
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            
        Returns:
            成本（美元）
        """
        try:
            model_type = self._get_model_type(model)
            pricing = self.model_pricing.get(model_type)
            
            if not pricing:
                logger.warning(f"未找到模型 {model} 的定价信息")
                return 0.0
            
            input_cost = (input_tokens / 1000) * pricing["input"]
            output_cost = (output_tokens / 1000) * pricing["output"]
            
            return input_cost + output_cost
        except Exception as e:
            logger.error(f"计算成本失败: {e}")
            return 0.0
    
    def _get_model_type(self, model: str) -> Optional[ModelType]:
        """根据模型名称获取模型类型"""
        for model_type in ModelType:
            if model_type.value in model.lower():
                return model_type
        return None
    
    def record_api_call(self, model: str, prompt: str, response: str, 
                       input_tokens: int, output_tokens: int, success: bool = True, 
                       error_message: Optional[str] = None) -> None:
        """
        记录API调用记录
        
        Args:
            model: 模型名称
            prompt: 输入提示
            response: 模型响应
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            success: 是否成功
            error_message: 错误信息
        """
        try:
            cost = self.calculate_api_call_cost(model, input_tokens, output_tokens)
            
            record = APICallRecord(
                timestamp=time.time(),
                model=model,
                prompt=prompt,
                response=response,
                token_usage=TokenUsage(input_tokens, output_tokens, 0, cost),
                cost=cost,
                success=success,
                error_message=error_message
            )
            
            self.api_records.append(record)
            
            # 更新统计信息
            self.token_stats[model]["input_tokens"] += input_tokens
            self.token_stats[model]["output_tokens"] += output_tokens
            self.token_stats[model]["total_tokens"] += input_tokens + output_tokens
            self.token_stats[model]["total_cost"] += cost
            self.token_stats[model]["call_count"] += 1
            
            if success:
                logger.info(f"API调用记录成功 - 模型: {model}, 输入: {input_tokens}, 输出: {output_tokens}, 成本: ${cost:.4f}")
            else:
                logger.warning(f"API调用记录失败 - 模型: {model}, 错误: {error_message}")
                
        except Exception as e:
            logger.error(f"记录API调用失败: {e}")
    
    def get_usage_summary(self) -> Dict:
        """
        获取使用摘要
        
        Returns:
            使用摘要字典
        """
        summary = {
            "total_calls": len(self.api_records),
            "total_cost": sum(record.cost for record in self.api_records),
            "total_tokens": sum(record.token_usage.total_tokens for record in self.api_records),
            "successful_calls": sum(1 for record in self.api_records if record.success),
            "failed_calls": sum(1 for record in self.api_records if not record.success),
            "model_stats": dict(self.token_stats),
            "time_range": {
                "start": min(record.timestamp for record in self.api_records) if self.api_records else None,
                "end": max(record.timestamp for record in self.api_records) if self.api_records else None
            }
        }
        
        return summary
    
    def export_usage_report(self, output_path: str = "token_usage_report.json") -> None:
        """
        导出使用报告
        
        Args:
            output_path: 输出文件路径
        """
        try:
            summary = self.get_usage_summary()
            
            # 添加详细的API记录
            detailed_records = []
            for record in self.api_records:
                detailed_records.append({
                    "timestamp": record.timestamp,
                    "model": record.model,
                    "input_tokens": record.token_usage.input_tokens,
                    "output_tokens": record.token_usage.output_tokens,
                    "total_tokens": record.token_usage.total_tokens,
                    "cost": record.cost,
                    "success": record.success,
                    "error_message": record.error_message,
                    "prompt_preview": record.prompt[:200] + "..." if len(record.prompt) > 200 else record.prompt,
                    "response_preview": record.response[:200] + "..." if len(record.response) > 200 else record.response
                })
            
            report = {
                "summary": summary,
                "detailed_records": detailed_records,
                "generated_at": time.time()
            }
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"使用报告已导出到: {output_path}")
            
        except Exception as e:
            logger.error(f"导出使用报告失败: {e}")
    
    def analyze_text_efficiency(self, text: str, model: str) -> Dict:
        """
        分析文本效率
        
        Args:
            text: 要分析的文本
            model: 模型名称
            
        Returns:
            效率分析结果
        """
        try:
            tokens = self.count_tokens(text, model)
            char_count = len(text)
            
            # 计算token/char比率
            token_char_ratio = tokens / char_count if char_count > 0 else 0
            
            # 估算成本（假设为输出token）
            cost = self.calculate_api_call_cost(model, 0, tokens)
            
            analysis = {
                "text_length": char_count,
                "token_count": tokens,
                "token_char_ratio": token_char_ratio,
                "estimated_cost": cost,
                "efficiency_rating": self._get_efficiency_rating(token_char_ratio)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析文本效率失败: {e}")
            return {}
    
    def _get_efficiency_rating(self, token_char_ratio: float) -> str:
        """获取效率评级"""
        if token_char_ratio < 0.25:
            return "优秀"
        elif token_char_ratio < 0.35:
            return "良好"
        elif token_char_ratio < 0.45:
            return "一般"
        else:
            return "较差"
    
    def batch_analyze_texts(self, texts: List[str], model: str) -> List[Dict]:
        """
        批量分析文本
        
        Args:
            texts: 文本列表
            model: 模型名称
            
        Returns:
            分析结果列表
        """
        results = []
        for i, text in enumerate(texts):
            try:
                analysis = self.analyze_text_efficiency(text, model)
                analysis["text_index"] = i
                analysis["text_preview"] = text[:100] + "..." if len(text) > 100 else text
                results.append(analysis)
            except Exception as e:
                logger.error(f"分析文本 {i} 失败: {e}")
                results.append({
                    "text_index": i,
                    "error": str(e)
                })
        
        return results
    
    def print_usage_report(self) -> None:
        """打印使用报告"""
        summary = self.get_usage_summary()
        
        print("\n" + "="*50)
        print("Token使用报告")
        print("="*50)
        print(f"总调用次数: {summary['total_calls']}")
        print(f"总成本: ${summary['total_cost']:.4f}")
        print(f"总Token数: {summary['total_tokens']}")
        print(f"成功调用: {summary['successful_calls']}")
        print(f"失败调用: {summary['failed_calls']}")
        
        if summary['time_range']['start']:
            from datetime import datetime
            start_time = datetime.fromtimestamp(summary['time_range']['start'])
            end_time = datetime.fromtimestamp(summary['time_range']['end'])
            print(f"时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} - {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n各模型统计:")
        print("-"*50)
        for model, stats in summary['model_stats'].items():
            print(f"模型: {model}")
            print(f"  调用次数: {stats['call_count']}")
            print(f"  输入Token: {stats['input_tokens']}")
            print(f"  输出Token: {stats['output_tokens']}")
            print(f"  总Token: {stats['total_tokens']}")
            print(f"  总成本: ${stats['total_cost']:.4f}")
            print()
    
    def clear_records(self) -> None:
        """清空所有记录"""
        self.api_records.clear()
        self.token_stats.clear()
        logger.info("所有记录已清空")


def main():
    """主函数 - 演示用法"""
    import os
    
    # 创建token计算器实例
    calculator = TokenCalculator()
    
    # 示例文本
    sample_texts = [
        "你好，我想了解一下今天的股票市场情况。",
        "请分析一下这只股票的技术指标：603619.SH，当前价格36.50，成交量100万手。",
        "基于MA5和MA20的金叉信号，建议买入该股票，止损位设置在35.00。"
    ]
    
    print("=== Token计算器演示 ===")
    
    # 1. 基本token计算
    print("\n1. 基本Token计算:")
    for i, text in enumerate(sample_texts):
        tokens = calculator.count_tokens(text, "deepseek-reasoner")
        print(f"文本 {i+1}: {len(text)} 字符 -> {tokens} tokens")
    
    # 2. 文本效率分析
    print("\n2. 文本效率分析:")
    for i, text in enumerate(sample_texts):
        analysis = calculator.analyze_text_efficiency(text, "deepseek-reasoner")
        print(f"文本 {i+1}:")
        print(f"  字符数: {analysis['text_length']}")
        print(f"  Token数: {analysis['token_count']}")
        print(f"  Token/字符比率: {analysis['token_char_ratio']:.3f}")
        print(f"  效率评级: {analysis['efficiency_rating']}")
        print(f"  估算成本: ${analysis['estimated_cost']:.4f}")
    
    # 3. 批量分析
    print("\n3. 批量分析结果:")
    batch_results = calculator.batch_analyze_texts(sample_texts, "deepseek-reasoner")
    for result in batch_results:
        print(f"文本 {result['text_index']+1}: {result['token_count']} tokens, {result['efficiency_rating']}")
    
    # 4. 模拟API调用记录
    print("\n4. 模拟API调用记录:")
    for i, text in enumerate(sample_texts):
        input_tokens = calculator.count_tokens(text, "deepseek-reasoner")
        output_tokens = max(1, int(input_tokens * 0.3))  # 模拟输出
        cost = calculator.calculate_api_call_cost("deepseek-reasoner", input_tokens, output_tokens)
        
        calculator.record_api_call(
            model="deepseek-reasoner",
            prompt=text,
            response=f"这是对文本的分析结果...",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            success=True
        )
        
        print(f"调用 {i+1}: 输入 {input_tokens} tokens, 输出 {output_tokens} tokens, 成本 ${cost:.4f}")
    
    # 5. 打印使用报告
    print("\n5. 使用报告:")
    calculator.print_usage_report()
    
    # 6. 导出报告
    calculator.export_usage_report("demo_token_report.json")
    print("\n演示完成！报告已保存到 demo_token_report.json")


if __name__ == "__main__":
    main()