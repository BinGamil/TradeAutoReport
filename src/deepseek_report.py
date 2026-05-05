"""Report generation helpers with DeepSeek, OpenAI, and local fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI

from .config import PATHS
from .logger import get_logger

logger = get_logger(__name__)

PROMPT_PATH = PATHS.prompts_dir / "cost_daily_report_prompt.md"


def _stringify(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    return str(value)


def _load_prompt_template() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("Prompt template missing at %s; using inline fallback template.", PROMPT_PATH)
        return (
            "You are a disciplined Chinese-language trading analyst. "
            "Write a concise premarket report for {ticker}. "
            "Market summary: {market_summary}. Indicators: {indicators}. "
            "Optional news: {news_summary}. Report type: {report_type}."
        )


def _build_prompt(
    ticker: str,
    market_summary: Any,
    indicators: Any,
    news_summary: Any | None,
    report_type: str,
) -> str:
    template = _load_prompt_template()
    return template.format(
        ticker=ticker,
        report_type=report_type,
        market_summary=_stringify(market_summary),
        indicators=_stringify(indicators),
        news_summary=_stringify(news_summary),
    )


def _fallback_report(
    ticker: str,
    market_summary: Any,
    indicators: Any,
    report_type: str,
) -> str:
    summary = market_summary if isinstance(market_summary, dict) else {}
    ind = indicators if isinstance(indicators, dict) else {}

    latest_close = summary.get("latest_close", "N/A")
    daily_change = summary.get("daily_percent_change", "N/A")
    ma20 = ind.get("ma20", "N/A")
    ma50 = ind.get("ma50", "N/A")
    ma200 = ind.get("ma200", "N/A")
    rsi = ind.get("rsi14", "N/A")
    macd_line = ind.get("macd_line", "N/A")
    macd_signal = ind.get("macd_signal", "N/A")
    macd_hist = ind.get("macd_histogram", "N/A")
    atr = ind.get("atr14", "N/A")
    timestamp = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m-%d %H:%M:%S %Z")

    bias = "偏强" if isinstance(daily_change, (int, float)) and daily_change >= 0 else "偏弱"
    if isinstance(rsi, (int, float)):
        if rsi >= 70:
            rsi_view = "偏热，需防冲高回落"
        elif rsi <= 30:
            rsi_view = "偏冷，存在修复空间"
        else:
            rsi_view = "中性偏平"
    else:
        rsi_view = "数据不足"

    report = f"""## 市场背景
{ticker} 当前处于{bias}结构，最新收盘价 {latest_close}，前一交易日变化 {daily_change}%。若盘前没有新的重大宏观或公司事件，优先把大盘情绪、零售板块表现和个股关键均线放在一起判断。

## 前一交易日复盘
前一交易日收盘价为 {latest_close}，前收盘价为 {summary.get("previous_close", "N/A")}。价格相对前一日变化 {daily_change}%，说明短线仍需要结合开盘后的承接力度确认。若开盘后放量但无法延续，需要警惕冲高回落。

## 基本面与催化
当前 fallback 数据没有接入实时基本面新闻，只能基于价格和技术结构生成计划。COST 这类会员制零售股通常需要关注同店销售、会员费、毛利率、财报指引、消费者支出和机构评级变化。

## 新闻与信息流
- 暂无可用实时新闻摘要。
- 若盘前出现财报、评级调整、机构持仓变化或消费数据，应优先重新评估开盘计划。
- 没有新闻催化时，交易重点回到价格对关键均线和支撑压力位的反应。

## 分析师快照
当前 fallback 数据未提供一致评级、目标价或隐含上涨空间。分析师观点可作为中期参考，但不应替代当日价格确认。

## 市场情绪拆解
- 利多：价格结构为{bias}，MA20 {ma20}，MA50 {ma50}，MA200 {ma200}。
- 利空：RSI14 为 {rsi}，{rsi_view}，若开盘后量能不足，容易出现假突破。
- 中性：MACD 线 {macd_line}，信号线 {macd_signal}，柱状图 {macd_hist}，需要看早盘动能是否继续扩张。

## 技术分析
MA20 {ma20}，MA50 {ma50}，MA200 {ma200}，用于判断中长期趋势方向。RSI14 {rsi}，{rsi_view}。MACD 线 {macd_line}，信号线 {macd_signal}，柱状图 {macd_hist}。ATR14 {atr}，可作为当日波动和止损距离参考。

## 交易方法说明
本报告使用趋势确认加关键价位反应的方法：先看价格是否站稳均线和前收盘附近，再看量能和 MACD 动能是否配合。没有明确确认时，以等待为主。

## 支撑压力位
- 第一支撑：前收盘附近 {latest_close}
- 第二支撑：MA20 附近 {ma20}
- 深层支撑：MA50 附近 {ma50}
- 第一压力：开盘后形成的盘前/早盘高点
- 趋势压力：若冲高靠近近期高位但量能不配合，应降低追价意愿。

## 交易计划（包括长期，波段和日内交易计划）
长期交易计划：若价格继续保持在 MA50 和 MA200 上方，长期结构仍以逢回调观察为主。入场思路是等待回踩 MA50 或重要支撑后企稳；触发条件是价格止跌并重新站回短期均线；目标看前高或趋势延续区；失效条件是跌破 MA200 且无法快速收复。

波段交易计划：波段重点看 MA20 与 MA50 的支撑效果。入场思路是回踩 MA20 附近出现承接，或突破早盘高点后回踩不破；确认条件是量能改善且 MACD 柱状图不继续收缩；目标看前高或上方压力区；若跌破 MA50 或放量走弱，则波段计划降级。

日内交易计划：日内以开盘后 15 到 30 分钟为确认窗口。若强势高开后回踩不破前收或盘前支撑，可考虑顺势观察；若高开低走并跌破关键支撑，避免追多；若横盘无量，优先等待二次方向。日内风险以 ATR14 {atr} 作为波动参考。

## 风控提醒
- 不在开盘第一笔情绪波动里追价。
- 先定义失效价位，再考虑仓位大小。
- 若大盘情绪和 COST 个股结构冲突，以市场风险为先。
- 若数据源不完整，应降低计划置信度。

## 信息来源与时间戳
- 价格数据与技术指标：yfinance 历史行情。
- AI 报告：本地 fallback 逻辑生成，DeepSeek 当前未返回可用正文。
- 生成时间：{timestamp}。"""
    return report


def _call_llm(api_key: str, base_url: str | None, model: str, prompt: str) -> str | None:
    """Call an OpenAI-compatible chat model and return stripped text on success."""

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a concise Chinese trading assistant focused on premarket planning.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    content = response.choices[0].message.content if response.choices else None
    if content and content.strip():
        return content.strip()
    return None


def generate_trading_report(
    ticker: str,
    market_summary: Any,
    indicators: Any,
    news_summary: Any | None = None,
    report_type: str = "premarket",
) -> str:
    """Generate a concise Chinese trading report with DeepSeek and fallback support."""

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip() or "deepseek-v4-flash"
    if not api_key:
        logger.warning("DEEPSEEK_API_KEY is not set; trying OpenAI backup if available.")
    prompt = _build_prompt(ticker, market_summary, indicators, news_summary, report_type)

    if api_key:
        try:
            content = _call_llm(api_key, "https://api.deepseek.com", model, prompt)
            if content:
                return content
            logger.warning("DeepSeek returned an empty response; trying OpenAI backup if available.")
        except Exception as exc:  # pragma: no cover - network/provider variability
            logger.exception("DeepSeek report generation failed: %s", exc)

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    if openai_key:
        try:
            content = _call_llm(openai_key, None, openai_model, prompt)
            if content:
                return content
            logger.warning("OpenAI backup returned an empty response; using fallback report.")
        except Exception as exc:  # pragma: no cover - network/provider variability
            logger.exception("OpenAI backup report generation failed: %s", exc)
    else:
        logger.info("OPENAI_API_KEY is not set; skipping OpenAI backup.")

    return _fallback_report(ticker, market_summary, indicators, report_type)
