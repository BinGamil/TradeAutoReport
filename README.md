# TradeAutoReport

Automated daily premarket stock trading report system.

This project fetches daily market data for `COST` with `yfinance`, calculates technical indicators, and generates a Markdown premarket report with DeepSeek. It is structured so we can later add Gmail email delivery, Notion journal writing, news summaries, and multiple tickers.

Current features:

- MA5
- MA20
- MA50
- MA200
- RSI14
- MACD line, signal, and histogram
- ATR14
- DeepSeek-generated trading report with fallback behavior
- Markdown report output under `reports/YYYY-MM-DD_COST_premarket.md`
- GitHub Actions scheduled automation and manual dispatch support

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
- `REPORT_TICKER` if you want to override the default `COST`
- `REPORT_TYPE` if you want to override the default `premarket`
- `OPENAI_API_KEY` and `OPENAI_MODEL` if you want an OpenAI backup path

## Run locally

From the project root:

```bash
python src/main.py
```

You can also use `python -m src.main` if you prefer module execution.

That will fetch at least one year of daily data for the selected ticker, calculate indicators, generate the DeepSeek report, and save the Markdown output under `reports/`. If DeepSeek is unavailable, the program tries OpenAI when `OPENAI_API_KEY` is set. If both fail or are missing, it falls back to a rule-based Chinese report.

## GitHub Actions

The workflow file is `.github/workflows/daily_report.yml`.

It runs automatically Monday through Friday at `12:35 UTC`, which matches `8:35 AM America/Toronto` during daylight saving time.

### GitHub Secrets

Add this secret in your repository settings:

- `DEEPSEEK_API_KEY`

Optional repository variables or workflow env values:

- `DEEPSEEK_MODEL` defaults to `deepseek-v4-flash`
- `REPORT_TICKER` defaults to `COST`
- `REPORT_TYPE` defaults to `premarket`

### Manual trigger

Use the `workflow_dispatch` button in GitHub Actions and provide:

- `ticker` defaults to `COST`
- `report_type` defaults to `premarket`

The workflow installs dependencies, runs `python src/main.py`, and uploads any generated Markdown files from `reports/` as artifacts.

## Notes

- Generated reports are not committed automatically.
- Gmail, Notion, and news summaries will come in later phases.
