#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token使用监控器 - 集成到DeepSniper系统中
用于监控和优化LLM调用的token使用情况
"""

import sys
import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# 导入现有的DeepSniper组件
from core.llm_client import DeepSeekClient
from config.config import Config
from token_calculator import TokenCalculator, ModelType

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    """告警配置"""
    daily_cost_limit: float = 10.0  # 每日成本限制（美元）
    daily_token_limit: int = 100000  # 每日token限制
    single_call_cost_limit: float = 5.0  # 单次调用成本限制
    efficiency_threshold: float = 0.4  # 效率阈值（token/字符比率超过此值时告警）
    consecutive_failures: int = 3  # 连续失败次数告警


class TokenUsageMonitor:
    """Token使用监控器"""
    
    def __init__(self, alert_config: Optional[AlertConfig] = None):
        """
        初始化Token使用监控器
        
        Args:
            alert_config: 告警配置
        """
        self.token_calculator = TokenCalculator()
        self.alert_config = alert_config or AlertConfig()
        
        # 监控数据
        self.daily_usage = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_cost": 0.0,
            "total_tokens": 0,
            "call_count": 0,
            "model_usage": {},
            "start_time": time.time()
        }
        
        # 告警记录
        self.alerts = []
        
        # 性能优化建议
        self.optimization_suggestions = []
        
        logger.info("Token使用监控器初始化完成")
    
    def monitor_llm_call(self, model: str, prompt: str, response: str, 
                        success: bool = True, error_message: Optional[str] = None) -> Dict:
        """
        监控LLM调用
        
        Args:
            model: 模型名称
            prompt: 输入提示
            response: 模型响应
            success: 是否成功
            error_message: 错误信息
            
        Returns:
            监控结果
        """
        try:
            # 计算token使用情况
            input_tokens = self.token_calculator.count_tokens(prompt, model)
            output_tokens = self.token_calculator.count_tokens(response, model) if success else 0
            cost = self.token_calculator.calculate_api_call_cost(model, input_tokens, output_tokens)
            
            # 记录API调用
            self.token_calculator.record_api_call(
                model=model,
                prompt=prompt,
                response=response,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                success=success,
                error_message=error_message
            )
            
            # 更新每日使用统计
            self._update_daily_usage(model, input_tokens, output_tokens, cost, success)
            
            # 检查告警
            alerts = self._check_alerts(model, input_tokens, output_tokens, cost, success)
            
            # 生成性能分析
            performance_analysis = self._analyze_performance(prompt, response, model)
            
            # 记录优化建议
            self._record_optimization_suggestions(prompt, response, model, performance_analysis)
            
            result = {
                "timestamp": time.time(),
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": cost,
                "success": success,
                "alerts": alerts,
                "performance_analysis": performance_analysis,
                "daily_usage": self.daily_usage.copy()
            }
            
            if not success:
                result["error_message"] = error_message
            
            return result
            
        except Exception as e:
            logger.error(f"监控LLM调用失败: {e}")
            return {
                "timestamp": time.time(),
                "model": model,
                "success": False,
                "error": str(e)
            }
    
    def _update_daily_usage(self, model: str, input_tokens: int, output_tokens: int, 
                           cost: float, success: bool) -> None:
        """更新每日使用统计"""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # 如果日期变化，重置统计
            if current_date != self.daily_usage["date"]:
                self.daily_usage = {
                    "date": current_date,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "call_count": 0,
                    "model_usage": {},
                    "start_time": time.time()
                }
            
            # 更新统计
            self.daily_usage["total_cost"] += cost
            self.daily_usage["total_tokens"] += input_tokens + output_tokens
            self.daily_usage["call_count"] += 1
            
            # 更新模型使用统计
            if model not in self.daily_usage["model_usage"]:
                self.daily_usage["model_usage"][model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost": 0.0,
                    "call_count": 0
                }
            
            model_stats = self.daily_usage["model_usage"][model]
            model_stats["input_tokens"] += input_tokens
            model_stats["output_tokens"] += output_tokens
            model_stats["total_tokens"] += input_tokens + output_tokens
            model_stats["cost"] += cost
            model_stats["call_count"] += 1
            
        except Exception as e:
            logger.error(f"更新每日使用统计失败: {e}")
    
    def _check_alerts(self, model: str, input_tokens: int, output_tokens: int, 
                     cost: float, success: bool) -> List[Dict]:
        """检查告警条件"""
        alerts = []
        
        try:
            # 检查单次调用成本
            if cost > self.alert_config.single_call_cost_limit:
                alert = {
                    "type": "cost_limit_exceeded",
                    "message": f"单次调用成本 ${cost:.4f} 超过限制 ${self.alert_config.single_call_cost_limit}",
                    "severity": "high",
                    "timestamp": time.time()
                }
                alerts.append(alert)
                self.alerts.append(alert)
            
            # 检查每日成本
            if self.daily_usage["total_cost"] > self.alert_config.daily_cost_limit:
                alert = {
                    "type": "daily_cost_limit_exceeded",
                    "message": f"每日成本 ${self.daily_usage['total_cost']:.4f} 超过限制 ${self.alert_config.daily_cost_limit}",
                    "severity": "high",
                    "timestamp": time.time()
                }
                alerts.append(alert)
                self.alerts.append(alert)
            
            # 检查每日token限制
            if self.daily_usage["total_tokens"] > self.alert_config.daily_token_limit:
                alert = {
                    "type": "daily_token_limit_exceeded",
                    "message": f"每日Token数 {self.daily_usage['total_tokens']} 超过限制 {self.alert_config.daily_token_limit}",
                    "severity": "medium",
                    "timestamp": time.time()
                }
                alerts.append(alert)
                self.alerts.append(alert)
            
            # 检查连续失败
            if not success:
                recent_failures = [a for a in self.alerts[-10:] if a["type"] == "api_failure"]
                if len(recent_failures) >= self.alert_config.consecutive_failures:
                    alert = {
                        "type": "consecutive_failures",
                        "message": f"连续 {len(recent_failures)} 次API调用失败",
                        "severity": "high",
                        "timestamp": time.time()
                    }
                    alerts.append(alert)
                    self.alerts.append(alert)
            
        except Exception as e:
            logger.error(f"检查告警失败: {e}")
        
        return alerts
    
    def _analyze_performance(self, prompt: str, response: str, model: str) -> Dict:
        """分析性能"""
        try:
            # 分析提示效率
            prompt_analysis = self.token_calculator.analyze_text_efficiency(prompt, model)
            
            # 分析响应效率
            response_analysis = self.token_calculator.analyze_text_efficiency(response, model)
            
            # 计算输入输出比率
            input_output_ratio = (response_analysis['token_count'] / prompt_analysis['token_count']) if prompt_analysis['token_count'] > 0 else 0
            
            # 生成性能评分
            performance_score = self._calculate_performance_score(prompt_analysis, response_analysis, input_output_ratio)
            
            return {
                "prompt_efficiency": prompt_analysis,
                "response_efficiency": response_analysis,
                "input_output_ratio": input_output_ratio,
                "performance_score": performance_score,
                "recommendations": self._generate_performance_recommendations(prompt_analysis, response_analysis)
            }
            
        except Exception as e:
            logger.error(f"性能分析失败: {e}")
            return {}
    
    def _calculate_performance_score(self, prompt_analysis: Dict, response_analysis: Dict, 
                                   input_output_ratio: float) -> float:
        """计算性能评分"""
        try:
            score = 100.0
            
            # 根据效率调整分数
            if prompt_analysis['efficiency_rating'] == '较差':
                score -= 20
            elif prompt_analysis['efficiency_rating'] == '一般':
                score -= 10
            
            if response_analysis['efficiency_rating'] == '较差':
                score -= 15
            elif response_analysis['efficiency_rating'] == '一般':
                score -= 5
            
            # 根据输入输出比率调整分数
            if input_output_ratio > 0.8:
                score -= 10  # 输出过多可能不够精炼
            elif input_output_ratio < 0.2:
                score -= 5   # 输出过少可能不够详细
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"计算性能评分失败: {e}")
            return 0.0
    
    def _generate_performance_recommendations(self, prompt_analysis: Dict, response_analysis: Dict) -> List[str]:
        """生成性能优化建议"""
        recommendations = []
        
        try:
            # 提示优化建议
            if prompt_analysis['efficiency_rating'] == '较差':
                recommendations.append("提示文本过于冗长，建议精简内容，去除不必要的描述")
            elif prompt_analysis['efficiency_rating'] == '一般':
                recommendations.append("提示文本可以进一步优化，保持简洁明了")
            
            # 响应优化建议
            if response_analysis['efficiency_rating'] == '较差':
                recommendations.append("模型响应过于冗长，建议优化提示词以获得更简洁的回复")
            elif response_analysis['efficiency_rating'] == '一般':
                recommendations.append("模型响应可以更精炼，考虑调整提示词结构")
            
            # 基于比率的建议
            if response_analysis['token_count'] / prompt_analysis['token_count'] > 0.8:
                recommendations.append("输出内容相对输入过多，建议要求更简洁的回复")
            
        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
        
        return recommendations
    
    def _record_optimization_suggestions(self, prompt: str, response: str, model: str, 
                                       performance_analysis: Dict) -> None:
        """记录优化建议"""
        try:
            if performance_analysis and performance_analysis.get("recommendations"):
                suggestion = {
                    "timestamp": time.time(),
                    "model": model,
                    "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                    "performance_score": performance_analysis.get("performance_score", 0),
                    "recommendations": performance_analysis["recommendations"]
                }
                self.optimization_suggestions.append(suggestion)
                
                # 只保留最近的建议
                if len(self.optimization_suggestions) > 20:
                    self.optimization_suggestions = self.optimization_suggestions[-20:]
                    
        except Exception as e:
            logger.error(f"记录优化建议失败: {e}")
    
    def get_daily_report(self) -> Dict:
        """获取每日报告"""
        try:
            # 计算运行时长
            runtime = time.time() - self.daily_usage["start_time"]
            avg_tokens_per_call = self.daily_usage["total_tokens"] / self.daily_usage["call_count"] if self.daily_usage["call_count"] > 0 else 0
            avg_cost_per_call = self.daily_usage["total_cost"] / self.daily_usage["call_count"] if self.daily_usage["call_count"] > 0 else 0
            
            report = {
                "date": self.daily_usage["date"],
                "runtime_seconds": runtime,
                "total_calls": self.daily_usage["call_count"],
                "total_tokens": self.daily_usage["total_tokens"],
                "total_cost": self.daily_usage["total_cost"],
                "avg_tokens_per_call": avg_tokens_per_call,
                "avg_cost_per_call": avg_cost_per_call,
                "model_usage": self.daily_usage["model_usage"],
                "alerts_count": len(self.alerts),
                "optimization_suggestions_count": len(self.optimization_suggestions),
                "cost_efficiency": self._calculate_cost_efficiency(),
                "token_efficiency": self._calculate_token_efficiency()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"生成每日报告失败: {e}")
            return {}
    
    def _calculate_cost_efficiency(self) -> Dict:
        """计算成本效率"""
        try:
            if self.daily_usage["total_cost"] == 0:
                return {"efficiency": "N/A", "recommendations": []}
            
            # 计算每千token成本
            cost_per_1k_tokens = (self.daily_usage["total_cost"] / self.daily_usage["total_tokens"]) * 1000
            
            efficiency = "优秀"
            recommendations = []
            
            if cost_per_1k_tokens > 1.0:
                efficiency = "较差"
                recommendations.append("成本偏高，建议使用更经济的模型或优化提示词")
            elif cost_per_1k_tokens > 0.5:
                efficiency = "一般"
                recommendations.append("成本适中，可以考虑进一步优化")
            
            return {
                "cost_per_1k_tokens": cost_per_1k_tokens,
                "efficiency": efficiency,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"计算成本效率失败: {e}")
            return {"efficiency": "N/A", "recommendations": []}
    
    def _calculate_token_efficiency(self) -> Dict:
        """计算Token效率"""
        try:
            if self.daily_usage["call_count"] == 0:
                return {"avg_tokens_per_call": 0, "efficiency": "N/A"}
            
            avg_tokens_per_call = self.daily_usage["total_tokens"] / self.daily_usage["call_count"]
            
            efficiency = "优秀"
            recommendations = []
            
            if avg_tokens_per_call > 5000:
                efficiency = "较差"
                recommendations.append("单次调用token过多，建议拆分请求或优化提示词")
            elif avg_tokens_per_call > 2000:
                efficiency = "一般"
                recommendations.append("单次调用token适中，可以考虑进一步优化")
            
            return {
                "avg_tokens_per_call": avg_tokens_per_call,
                "efficiency": efficiency,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"计算Token效率失败: {e}")
            return {"avg_tokens_per_call": 0, "efficiency": "N/A", "recommendations": []}
    
    def export_monitoring_report(self, output_path: str = "token_monitoring_report.json") -> None:
        """导出监控报告"""
        try:
            report = {
                "daily_report": self.get_daily_report(),
                "recent_alerts": self.alerts[-10:],  # 最近10个告警
                "recent_optimization_suggestions": self.optimization_suggestions[-10:],  # 最近10个优化建议
                "export_timestamp": time.time()
            }
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"监控报告已导出到: {output_path}")
            
        except Exception as e:
            logger.error(f"导出监控报告失败: {e}")


class EnhancedLLMClient:
    """增强的LLM客户端，集成Token监控"""
    
    def __init__(self, monitor: TokenUsageMonitor):
        """
        初始化增强的LLM客户端
        
        Args:
            monitor: Token使用监控器
        """
        self.monitor = monitor
        self.llm_client = DeepSeekClient()
        logger.info("增强LLM客户端初始化完成")
    
    def get_analysis_with_monitoring(self, prompt_template: str, **kwargs) -> Dict:
        """
        获取分析结果，同时进行Token监控
        
        Args:
            prompt_template: 提示模板
            **kwargs: 模板参数
            
        Returns:
            分析结果
        """
        try:
            # 格式化提示
            prompt = prompt_template.format(**kwargs)
            
            # 调用LLM
            result = self.llm_client.get_analysis(prompt_template, **kwargs)
            
            # 监控调用
            monitoring_result = self.monitor.monitor_llm_call(
                model=self.llm_client.model,
                prompt=prompt,
                response=str(result) if result else "",
                success=True
            )
            
            # 添加监控信息到结果
            result["_monitoring"] = {
                "input_tokens": monitoring_result["input_tokens"],
                "output_tokens": monitoring_result["output_tokens"],
                "total_tokens": monitoring_result["total_tokens"],
                "cost": monitoring_result["cost"],
                "performance_score": monitoring_result.get("performance_analysis", {}).get("performance_score", 0)
            }
            
            return result
            
        except Exception as e:
            # 监控失败调用
            monitoring_result = self.monitor.monitor_llm_call(
                model=self.llm_client.model,
                prompt=prompt_template.format(**kwargs),
                response="",
                success=False,
                error_message=str(e)
            )
            
            logger.error(f"LLM调用失败: {e}")
            return {"error": str(e), "_monitoring": monitoring_result}


def main():
    """主函数 - 演示使用方法"""
    print("Token使用监控器演示")
    print("="*50)
    
    # 创建监控器
    monitor = TokenUsageMonitor()
    
    # 创建增强的LLM客户端
    enhanced_client = EnhancedLLMClient(monitor)
    
    # 模拟一些LLM调用
    test_prompts = [
        {"template": "分析股票{symbol}的技术面，当前价格{price}。", "symbol": "603619", "price": "36.50"},
        {"template": "总结今天的市场行情。", "symbol": None, "price": None},
        {"template": "评估股票{symbol}的投资风险。", "symbol": "000858", "price": None},
    ]
    
    print("模拟LLM调用...")
    for i, prompt_data in enumerate(test_prompts):
        try:
            result = enhanced_client.get_analysis_with_monitoring(**prompt_data)
            print(f"调用 {i+1}: 成功，Token: {result['_monitoring']['total_tokens']}, 成本: ${result['_monitoring']['cost']:.4f}")
        except Exception as e:
            print(f"调用 {i+1}: 失败 - {e}")
    
    # 生成报告
    print("\n生成监控报告...")
    daily_report = monitor.get_daily_report()
    
    print(f"日期: {daily_report['date']}")
    print(f"总调用次数: {daily_report['total_calls']}")
    print(f"总Token数: {daily_report['total_tokens']}")
    print(f"总成本: ${daily_report['total_cost']:.4f}")
    print(f"平均每次调用Token数: {daily_report['avg_tokens_per_call']:.1f}")
    print(f"平均每次调用成本: ${daily_report['avg_cost_per_call']:.4f}")
    print(f"成本效率: {daily_report['cost_efficiency']['efficiency']}")
    print(f"Token效率: {daily_report['token_efficiency']['efficiency']}")
    
    # 导出报告
    monitor.export_monitoring_report("demo_monitoring_report.json")
    print("\n监控报告已导出到 demo_monitoring_report.json")


if __name__ == "__main__":
    main()