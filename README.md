# TradeAutoReport

Phase 2 of an automated daily premarket stock trading report system.

This version fetches daily market data for `COST` with `yfinance`, calculates technical indicators, and generates a concise Chinese premarket report with DeepSeek.

- MA5
- MA20
- MA50
- MA200
- RSI14
- MACD line, signal, and histogram
- ATR14
- DeepSeek-generated trading report with fallback behavior

## Requirements

- Python 3.11
- Internet access for `yfinance` to download price history
- `DEEPSEEK_API_KEY` for AI-generated reports
- Optional: `DEEPSEEK_MODEL` to override the default model name
- Optional backup: `OPENAI_API_KEY` and `OPENAI_MODEL` if you want OpenAI to be used when DeepSeek fails

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

Copy `.env.example` to `.env` and set:

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL` if you want to override the default `deepseek-v4-flash`
- `OPENAI_API_KEY` and `OPENAI_MODEL` if you want an OpenAI backup path

## Run locally

From the project root:

```bash
python -m src.main
```

That will fetch at least one year of daily data for `COST`, calculate indicators, and print the DeepSeek report. If DeepSeek is unavailable, the program tries OpenAI when `OPENAI_API_KEY` is set. If both fail or are missing, it falls back to a rule-based Chinese report.

## Notes

- This phase does not generate Markdown files yet.
- Gmail, Notion, and GitHub Actions automation will come in later phases.
