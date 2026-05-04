"""HTML rendering helpers for the DeepSeek trading report."""

from __future__ import annotations

import re
from datetime import datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

from .config import PATHS
from .logger import get_logger

logger = get_logger(__name__)

REPORT_TZ = ZoneInfo("America/Toronto")


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_price(value: Any) -> str:
    number = _as_float(value)
    return "数据不足" if number is None else f"${number:.2f}"


def _fmt_pct(value: Any) -> str:
    number = _as_float(value)
    return "数据不足" if number is None else f"{number:.2f}%"


def _fmt_number(value: Any) -> str:
    number = _as_float(value)
    return "数据不足" if number is None else f"{number:.2f}"


def _fmt_text(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return text or "数据不足"


def _derive_stance(market_summary: dict[str, Any], indicators: dict[str, Any]) -> tuple[str, str]:
    daily_change = _as_float(market_summary.get("daily_percent_change"))
    latest_close = _as_float(market_summary.get("latest_close"))
    ma20 = _as_float(indicators.get("ma20"))
    rsi = _as_float(indicators.get("rsi14"))

    if latest_close is not None and ma20 is not None and latest_close > ma20 and (daily_change or 0) >= 0:
        if rsi is not None and rsi >= 60:
            return "偏多", "good"
        return "偏多", "good"
    if latest_close is not None and ma20 is not None and latest_close < ma20 and (daily_change or 0) < 0:
        return "偏空", "bad"
    return "中性", "neutral"


def _parse_sections(report: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title = "报告正文"
    current_lines: list[str] = []

    for line in report.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_lines or current_title != "报告正文":
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = stripped[3:].strip()
            current_lines = []
            continue
        if stripped.startswith("# "):
            continue
        current_lines.append(line)

    if current_lines or current_title != "报告正文":
        sections.append((current_title, "\n".join(current_lines).strip()))

    return sections


def _render_body(text: str) -> str:
    if not text.strip():
        return '<p class="muted">数据不足</p>'

    parts: list[str] = []
    paragraph: list[str] = []
    bullets: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            parts.append(f"<p>{escape(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_bullets() -> None:
        if bullets:
            items = "".join(f"<li>{escape(item)}</li>" for item in bullets)
            parts.append(f"<ul>{items}</ul>")
            bullets.clear()

    bullet_pattern = re.compile(r"^(?:[-*•]|\d+\.)\s+(.*)$")

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            flush_bullets()
            continue

        match = bullet_pattern.match(line)
        if match:
            flush_paragraph()
            bullets.append(match.group(1).strip())
            continue

        flush_bullets()
        paragraph.append(line)

    flush_paragraph()
    flush_bullets()
    return "".join(parts)


def _build_metric_cards(market_summary: dict[str, Any], indicators: dict[str, Any]) -> str:
    cards = [
        ("最新收盘", _fmt_price(market_summary.get("latest_close"))),
        ("前收盘", _fmt_price(market_summary.get("previous_close"))),
        ("日涨跌幅", _fmt_pct(market_summary.get("daily_percent_change"))),
        ("MA20", _fmt_price(indicators.get("ma20"))),
        ("RSI14", _fmt_number(indicators.get("rsi14"))),
        ("ATR14", _fmt_price(indicators.get("atr14"))),
    ]
    return "".join(
        f'<div class="card metric-card"><div class="label">{escape(label)}</div><div class="value">{escape(value)}</div></div>'
        for label, value in cards
    )


def _build_indicator_cards(indicators: dict[str, Any]) -> str:
    cards = [
        (
            "趋势结构",
            [
                f"MA5 / MA20：{_fmt_price(indicators.get('ma5'))} / {_fmt_price(indicators.get('ma20'))}",
                f"MA50 / MA200：{_fmt_price(indicators.get('ma50'))} / {_fmt_price(indicators.get('ma200'))}",
            ],
        ),
        (
            "动量信号",
            [
                f"RSI14：{_fmt_number(indicators.get('rsi14'))}",
                f"MACD线：{_fmt_number(indicators.get('macd_line'))}",
                f"MACD信号：{_fmt_number(indicators.get('macd_signal'))}",
                f"MACD柱状：{_fmt_number(indicators.get('macd_histogram'))}",
            ],
        ),
        (
            "波动参考",
            [
                f"ATR14：{_fmt_price(indicators.get('atr14'))}",
                "用于评估盘前波动空间与止损距离。",
            ],
        ),
    ]
    return "".join(
        f'<div class="card"><h3>{escape(title)}</h3>' + "".join(f"<p>{escape(line)}</p>" for line in lines) + "</div>"
        for title, lines in cards
    )


def _build_sections(sections: list[tuple[str, str]]) -> str:
    if not sections:
        return '<div class="card"><p class="muted">未解析到结构化段落。</p></div>'
    return "".join(
        f'<div class="plan-card"><span class="plan-meta">{escape(title)}</span>{_render_body(body)}</div>'
        for title, body in sections
    )


def build_html_report(
    ticker: str,
    report_type: str,
    report: str,
    market_summary: dict[str, Any],
    indicators: dict[str, Any],
    generated_at: datetime | None = None,
) -> str:
    """Build a polished HTML version of the generated report."""

    generated_at = generated_at or datetime.now(REPORT_TZ)
    sections = _parse_sections(report)
    section_map = {title: body for title, body in sections}
    headline = section_map.get("今日结论") or report.splitlines()[0].strip() or "DeepSeek Trading Report"
    stance, stance_class = _derive_stance(market_summary, indicators)
    section_cards = _build_sections(sections)

    summary_html = _render_body(
        (
            f"{headline}\n\n"
            f"报告类型：{report_type}\n"
            f"生成时间：{generated_at.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"当前结论：{stance}\n"
        )
    )

    technical_summary_lines = [
        f"收盘价 { _fmt_price(market_summary.get('latest_close')) }，前收盘 { _fmt_price(market_summary.get('previous_close')) }。",
        f"日涨跌幅 {_fmt_pct(market_summary.get('daily_percent_change'))}。",
        f"MA20 {_fmt_price(indicators.get('ma20'))}，MA50 {_fmt_price(indicators.get('ma50'))}，MA200 {_fmt_price(indicators.get('ma200'))}。",
        f"RSI14 {_fmt_number(indicators.get('rsi14'))}，ATR14 {_fmt_price(indicators.get('atr14'))}。",
    ]

    html_body = f"""
    <div class="toolbar">
      <div class="toolbar-left">
        <span class="brand">DeepSeek HTML Report</span>
        <span class="pill {stance_class}">{escape(stance)}</span>
      </div>
      <div class="toolbar-right">
        <span class="tool-chip">{escape(ticker.upper())}</span>
        <span class="tool-chip">{escape(report_type)}</span>
      </div>
    </div>

    <div class="hero">
      <h1>{escape(ticker.upper())} 深度盘前报告</h1>
      <p>{escape(_fmt_text(headline))}</p>
      <p class="muted">生成时间：{escape(generated_at.strftime('%Y-%m-%d %H:%M:%S %Z'))}</p>
    </div>

    <div class="summary">{summary_html}</div>

    <section>
      <h2>关键指标</h2>
      <div class="grid">{_build_metric_cards(market_summary, indicators)}</div>
    </section>

    <section>
      <h2>技术概览</h2>
      <div class="columns">
        {_build_indicator_cards(indicators)}
        <div class="card">
          <h3>盘前摘要</h3>
          <p>{escape(' '.join(technical_summary_lines))}</p>
        </div>
      </div>
    </section>

    <section>
      <h2>DeepSeek 分析</h2>
      <div class="plan-grid">{section_cards}</div>
    </section>

    <div class="footer">本报告由 DeepSeek 生成，并以 HTML 方式呈现，便于浏览和归档。</div>
    """

    html_document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(ticker.upper())} {escape(report_type.title())} Report</title>
<style>
:root {{
  --ink:#1f2937;
  --muted:#5b6472;
  --accent:#123b45;
  --line:#d6dde3;
  --good:#0f766e;
  --warn:#b45309;
  --bad:#b91c1c;
  --bg:#f6f1e8;
  --card:#ffffff;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font:16px/1.55 Arial, sans-serif; background:linear-gradient(180deg,#f6f1e8 0%,#f8fafc 100%); color:var(--ink); }}
.main {{ max-width:1120px; margin:0 auto; padding:32px 24px 72px; }}
.toolbar {{ display:flex; flex-wrap:wrap; gap:12px; align-items:center; justify-content:space-between; margin-bottom:18px; }}
.toolbar-left, .toolbar-right {{ display:flex; flex-wrap:wrap; gap:12px; align-items:center; }}
.brand {{ font-weight:700; color:#14213d; letter-spacing:.02em; }}
.tool-chip {{ border:1px solid var(--line); background:#fff; border-radius:999px; padding:6px 10px; color:#19324d; font-size:13px; font-weight:700; }}
.hero {{ border-left:8px solid var(--good); padding:8px 0 8px 24px; margin-bottom:28px; }}
.hero h1 {{ margin:0 0 8px; font-size:40px; line-height:1.1; color:#14213d; }}
.hero p {{ margin:6px 0; color:var(--muted); }}
.summary {{ background:rgba(255,255,255,.74); border:1px solid var(--line); border-radius:14px; padding:22px; margin:18px 0 28px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin:18px 0 28px; }}
.columns {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:18px; }}
.plan-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:18px; }}
.card, .plan-card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px 18px; box-shadow:0 10px 24px rgba(18,59,69,.06); }}
.metric-card .value {{ font-size:30px; font-weight:700; color:#14213d; }}
.card .label {{ color:var(--muted); font-size:13px; margin-bottom:8px; }}
.card .value {{ color:#14213d; }}
section {{ margin:28px 0; }}
section h2 {{ margin:0 0 14px; font-size:24px; color:#14213d; }}
section h3 {{ margin:18px 0 10px; font-size:18px; color:#19324d; }}
.plan-card h3 {{ margin:0 0 8px; }}
.plan-meta {{ display:inline-block; margin-bottom:12px; padding:5px 10px; border-radius:999px; background:#e8eef5; color:#19324d; font-size:12px; font-weight:700; }}
.plan-card p {{ margin:10px 0; }}
ul {{ margin:10px 0 0 20px; padding:0; }}
.pill {{ display:inline-flex; align-items:center; padding:6px 10px; border-radius:999px; font-size:13px; font-weight:700; background:#e7f4ef; color:#0f766e; }}
.pill.neutral {{ background:#fff4df; color:#b45309; }}
.pill.bad {{ background:#fde8e8; color:#b91c1c; }}
.pill.good {{ background:#e7f4ef; color:#0f766e; }}
.muted {{ color:var(--muted); }}
.footer {{ margin-top:38px; font-size:13px; color:var(--muted); }}
@media (max-width: 640px) {{
  .hero h1 {{ font-size:30px; }}
}}
</style>
</head>
<body>
<div class="main">
{html_body}
</div>
</body>
</html>
"""
    return html_document


def save_html_report(
    ticker: str,
    report_type: str,
    report: str,
    market_summary: dict[str, Any],
    indicators: dict[str, Any],
) -> str:
    """Save the HTML report next to the Markdown version."""

    timestamp = datetime.now(REPORT_TZ)
    reports_dir = PATHS.reports_dir
    reports_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{timestamp:%Y-%m-%d}_{ticker.upper()}_{report_type.strip().lower().replace(' ', '_')}.html"
    file_path = reports_dir / file_name
    content = build_html_report(
        ticker=ticker,
        report_type=report_type,
        report=report,
        market_summary=market_summary,
        indicators=indicators,
        generated_at=timestamp,
    )

    try:
        file_path.write_text(content, encoding="utf-8")
    except Exception as exc:  # pragma: no cover - filesystem variability
        logger.exception("Failed to write HTML report %s: %s", file_path, exc)
        raise

    return str(file_path)
