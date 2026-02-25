# Token计算器使用说明

## 概述

Token计算器是一个功能强大的工具，用于计算和管理各种LLM模型的token使用情况。它支持多种主流模型，提供详细的成本分析、性能监控和优化建议。

## 功能特性

### 核心功能
- **多模型支持**: 支持DeepSeek、GPT、Claude等多种主流LLM模型
- **精确计算**: 使用tiktoken库进行精确的token计算
- **成本分析**: 实时计算API调用成本，支持多种定价模型
- **性能监控**: 监控API调用性能，生成效率分析报告
- **使用统计**: 记录和分析token使用情况，生成详细统计报告

### 高级功能
- **批量分析**: 支持批量文本分析，提高效率
- **告警系统**: 自定义告警阈值，及时发现问题
- **优化建议**: 基于使用情况提供优化建议
- **数据导出**: 支持JSON格式的报告导出
- **系统集成**: 可与现有DeepSniper系统无缝集成

## 文件结构

```
DeepSniper/
├── token_calculator.py      # 主要的Token计算器类
├── token_usage_monitor.py   # Token使用监控器（集成到现有系统）
├── test_token_calculator.py # 测试和演示脚本
├── TOKEN_CALCULATOR_README.md  # 本文档
└── requirements.txt         # 依赖项列表
```

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 环境配置

确保在`config/secrets.env`文件中设置了必要的API密钥：

```bash
# OpenAI API密钥（用于token计算）
OPENAI_API_KEY=your_openai_api_key_here

# DeepSeek API密钥（用于实际调用）
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### 3. 模型配置

在`config/config.yaml`中配置LLM参数：

```yaml
llm:
  model_name: "deepseek-reasoner"
  base_url: "https://api.deepseek.com"
  temperature: 0.6
  max_tokens: 4096
```

## 使用方法

### 基本使用

```python
from token_calculator import TokenCalculator

# 创建计算器实例
calculator = TokenCalculator()

# 计算文本token数
text = "这是一个测试文本"
tokens = calculator.count_tokens(text, "deepseek-reasoner")
print(f"Token数量: {tokens}")

# 分析文本效率
analysis = calculator.analyze_text_efficiency(text, "deepseek-reasoner")
print(f"效率分析: {analysis}")

# 计算成本
cost = calculator.calculate_api_call_cost("deepseek-reasoner", 1000, 500)
print(f"成本: ${cost:.4f}")
```

### 批量分析

```python
# 批量分析多个文本
texts = [
    "文本1",
    "文本2",
    "文本3"
]

results = calculator.batch_analyze_texts(texts, "deepseek-reasoner")
for result in results:
    print(f"文本 {result['text_index']}: {result['token_count']} tokens")
```

### API调用监控

```python
# 记录API调用
calculator.record_api_call(
    model="deepseek-reasoner",
    prompt="分析股票603619",
    response="该股票技术面良好",
    input_tokens=150,
    output_tokens=80,
    success=True
)

# 获取使用摘要
summary = calculator.get_usage_summary()
print(f"总成本: ${summary['total_cost']:.4f}")
print(f"总Token数: {summary['total_tokens']}")

# 导出报告
calculator.export_usage_report("usage_report.json")
```

### 与现有系统集成

```python
from token_usage_monitor import TokenUsageMonitor, EnhancedLLMClient

# 创建监控器
monitor = TokenUsageMonitor()

# 创建增强的LLM客户端
enhanced_client = EnhancedLLMClient(monitor)

# 使用增强客户端进行LLM调用
result = enhanced_client.get_analysis_with_monitoring(
    "分析股票{symbol}的技术面",
    symbol="603619"
)

# 获取监控信息
monitoring_info = result["_monitoring"]
print(f"输入Token: {monitoring_info['input_tokens']}")
print(f"输出Token: {monitoring_info['output_tokens']}")
print(f"成本: ${monitoring_info['cost']:.4f}")
print(f"性能评分: {monitoring_info['performance_score']}")
```

## 支持的模型

### DeepSeek系列
- `deepseek-reasoner`: DeepSeek推理模型
- `deepseek-chat`: DeepSeek聊天模型

### OpenAI系列
- `gpt-4o`: GPT-4o模型
- `gpt-4o-mini`: GPT-4o Mini模型
- `gpt-4-turbo`: GPT-4 Turbo模型
- `gpt-4`: GPT-4模型
- `gpt-3.5-turbo`: GPT-3.5 Turbo模型
- `gpt-3.5-turbo-16k`: GPT-3.5 Turbo 16K模型

### Claude系列
- `claude-3-haiku`: Claude 3 Haiku模型
- `claude-3-sonnet`: Claude 3 Sonnet模型
- `claude-3-opus`: Claude 3 Opus模型

## 定价信息

所有模型的价格信息都内置在计算器中（每1K tokens的价格，单位：美元）：

| 模型 | 输入价格 | 输出价格 |
|------|----------|----------|
| deepseek-reasoner | $0.14 | $0.28 |
| deepseek-chat | $0.14 | $0.28 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $3.00 | $6.00 |
| gpt-4 | $3.00 | $6.00 |
| gpt-3.5-turbo | $0.50 | $1.50 |
| claude-3-sonnet | $3.00 | $15.00 |
| claude-3-opus | $15.00 | $75.00 |

## 性能分析

### 效率评级

计算器会根据token/字符比率对文本效率进行评级：

- **优秀**: < 0.25 (token/字符)
- **良好**: 0.25 - 0.35
- **一般**: 0.35 - 0.45
- **较差**: > 0.45

### 性能评分

性能评分基于以下因素：
- 文本效率
- 输入输出比率
- 响应质量

评分范围：0-100分，分数越高表示性能越好。

## 监控和告警

### 告警配置

可以通过`AlertConfig`类自定义告警阈值：

```python
from token_usage_monitor import AlertConfig

alert_config = AlertConfig(
    daily_cost_limit=10.0,        # 每日成本限制
    daily_token_limit=100000,     # 每日token限制
    single_call_cost_limit=5.0,   # 单次调用成本限制
    efficiency_threshold=0.4,     # 效率阈值
    consecutive_failures=3        # 连续失败次数
)

monitor = TokenUsageMonitor(alert_config)
```

### 告警类型

- **成本限制告警**: 当成本超过设定阈值时触发
- **Token限制告警**: 当token使用超过限制时触发
- **连续失败告警**: 当API连续失败时触发
- **效率告警**: 当文本效率过低时触发

## 报告和导出

### 使用报告

```python
# 获取使用摘要
summary = calculator.get_usage_summary()

# 打印报告
calculator.print_usage_report()

# 导出JSON报告
calculator.export_usage_report("report.json")
```

### 监控报告

```python
# 获取每日报告
daily_report = monitor.get_daily_report()

# 导出监控报告
monitor.export_monitoring_report("monitoring_report.json")
```

## 测试和验证

### 运行测试脚本

```bash
# 运行完整测试套件
python test_token_calculator.py

# 运行演示
python token_usage_monitor.py
```

### 测试内容

测试脚本包含以下测试：
1. 基本token计算功能
2. 文本效率分析
3. 批量分析功能
4. API调用记录
5. 成本计算功能
6. 模型定价信息
7. 导出功能
8. 系统集成测试

## 最佳实践

### 1. 优化提示词

- 保持提示词简洁明了
- 避免冗余信息
- 使用结构化格式
- 适当使用JSON格式

### 2. 成本控制

- 选择合适的模型
- 监控使用情况
- 设置合理的告警阈值
- 定期审查使用模式

### 3. 性能优化

- 分析文本效率
- 关注输入输出比率
- 使用批量分析
- 定期生成优化建议

### 4. 错误处理

- 监控API调用成功率
- 设置重试机制
- 记录错误信息
- 及时响应告警

## 故障排除

### 常见问题

1. **Token计算不准确**
   - 确保使用正确的模型编码
   - 检查文本是否包含特殊字符
   - 更新tiktoken库

2. **成本计算错误**
   - 验证模型定价信息
   - 检查token数量计算
   - 确认货币单位

3. **API调用失败**
   - 检查API密钥配置
   - 验证网络连接
   - 查看错误日志

4. **监控功能异常**
   - 检查告警配置
   - 验证数据记录
   - 查看监控日志

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查配置
print(calculator.config)

# 验证token计算
text = "测试文本"
tokens = calculator.count_tokens(text, "deepseek-reasoner")
print(f"Token计算结果: {tokens}")

# 检查API记录
print(f"记录数量: {len(calculator.api_records)}")
```

## 更新和维护

### 依赖更新

```bash
# 更新依赖包
pip install --upgrade -r requirements.txt

# 更新tiktoken
pip install --upgrade tiktoken
```

### 模型支持

如需添加新的模型支持：
1. 在`ModelType`枚举中添加新模型
2. 在`model_pricing`字典中添加定价信息
3. 更新编码器映射
4. 测试新模型的功能

### 配置更新

定期更新配置文件以反映最新的API设置和定价信息。

## 许可证

本项目遵循MIT许可证。详情请参阅LICENSE文件。

## 联系和支持

如有问题或建议，请通过以下方式联系：
- 创建GitHub Issue
- 发送邮件至项目维护者
- 查看项目Wiki和FAQ

---

**注意**: 本工具仅用于token使用情况的计算和分析，不保证API调用的成功性。请确保遵守相关API的使用条款和限制。