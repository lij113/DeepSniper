# DeepSniper

大模型辅助的 A 股选股与盘中信号系统。交易时段按时间片循环：刷新股票池，逐只计算技术指标、识别 K 线形态、抓取个股公告，交给 DeepSeek 给出结构化信号，高信心信号推送到微信。

## 工作流程

`scripts/run.py` 是守护进程，按交易时间切换状态：

| 时段 | 状态 | 动作 |
|---|---|---|
| 09:00–09:30 | 开盘前 | 每 5 分钟刷新股票池并分析 |
| 09:30–11:31、13:00–15:05 | 交易中 | 每 `SCAN_INTERVAL_MINUTES` 分钟（默认 15）刷新股票池并分析 |
| 11:31–12:59 | 午休 | 待机 |
| 15:05–15:30 | 收盘后 | 最后同步一次 |
| 其余时间、周末 | 待机 | 定时检查 |

每一轮分两步：

1. **刷新股票池**（`scripts/update_stock_pool.py`）：拉取全市场快照，只留主板、去掉 ST 和 5 元以下个股，按成交额和当日涨跌幅过滤；从高换手、放量、温和上涨三条路径取候选。涨停家数占比超过 2% 判为市场偏热，放宽当日涨幅、量比门槛和候选数量。多线程逐只拉 K 线，要求均线多头（MA5 在 MA20 上方、价格站上 MA20）、量能、RSI、ADX 达标，再按 RSI、均线位置、换手率、ADX、近期涨幅打分，写出主力池与观察池（默认各 10 只）到 `config/stock_pool.json`。
2. **深度分析与推送**（`scripts/main_quant.py`）：对池内每只股票拉取实时行情和日 K 线，把当天实时数据补进 K 线，计算均线、MACD、KDJ、RSI（Wilder 平滑）、ADX、SuperTrend、量比，识别看涨吞没、十字星、锤头线、N 型反包等形态，连同东方财富上最新 10 条个股公告交给 DeepSeek，要求以 JSON 返回信号、信心分和理由。信号为买入且信心不低于 70、当天没推送过的，经 WxPusher 推送到微信。

行情数据源请求失败时，会从代理接口提取新 IP 后重试；调用 DeepSeek 和推送时临时去掉代理、直接连接。

## 目录

```
scripts/run.py                 守护进程与时间片调度
scripts/update_stock_pool.py   全市场选股，生成股票池
scripts/main_quant.py          逐只分析、生成信号、推送
strategies/technical_analysis.py  技术指标与 K 线形态
utils/data_fetch.py            实时行情与 K 线缓存（efinance），个股公告（东方财富）
utils/deepseek_api.py          DeepSeek 调用与 JSON 解析
utils/notify.py                WxPusher 微信推送
utils/logger.py                日志（logs/run.log，按大小滚动）
config/config.example.json     配置模板
```

## 运行

```bash
pip install -r requirements.txt
cp config/config.example.json config/config.json   # 填入 DeepSeek、WxPusher 的密钥，代理接口可选
python scripts/update_stock_pool.py                # 单独刷新一次股票池
python scripts/run.py                              # 启动守护进程
```

`config/config.json`、`config/stock_pool.json`、`logs/`、`data_cache/` 不进仓库。

## 说明

本项目只产生提示信号，不自动下单，不构成投资建议。
