"""Report generation helpers with DeepSeek, OpenAI, and local fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

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

    report = f"""## 今日结论
{ticker} 当前属于{bias}结构，最新收盘价 {latest_close}，日内变化 {daily_change}。若盘前没有新的重大事件，优先按关键均线和开盘区间来处理，不追涨也不盲目抄底。

## 技术面分析
MA20 {ma20}，MA50 {ma50}，MA200 {ma200}，说明中期结构仍需结合开盘后的价格行为确认。RSI14 {rsi}，{rsi_view}。MACD 线 {macd_line}，信号线 {macd_signal}，柱状图 {macd_hist}，用于判断早盘动能是否延续。ATR14 {atr}，可作为当日波动参考。

## 支撑与阻力
优先观察昨日收盘附近、盘前高低点、MA20 和 MA50。上方若放量站稳盘前高点，才考虑顺势；下方若失守盘前低点或 MA20，需提高警惕。

## 今日交易计划
以 {report_type} 视角，围绕开盘前 15 到 30 分钟确认方向。若强势高开并回踩不破，找回踩跟随；若高开低走，则等待整理后再判断是否有二次上攻机会。若无清晰方向，宁可少做。

## 挂单建议
仅保留触发式计划单：突破盘前高点的顺势单、回踩 MA20 附近的确认单、跌破盘前低点后的防守单。所有单子都要配合明确止损，不在噪音区追单。

## 风险管理
单笔风险控制在计划仓位的可承受范围内，先定义止损，再决定仓位。若开盘波动异常放大，主动缩小仓位。若市场情绪和个股结构冲突，以市场情绪为先。

## Journal Summary
今天的重点不是预测，而是确认：价格是否尊重关键均线，早盘是否给出可重复的入场信号，以及执行是否遵守纪律。"""
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
