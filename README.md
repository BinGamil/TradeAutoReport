# TradeAutoReport

Automated daily premarket stock trading report system.

This project fetches daily market data for supported tickers such as `COST` and `MSFT` with `yfinance`, calculates technical indicators, generates a DeepSeek premarket report in both Markdown and HTML, and can send the latest HTML report by Gmail. It is structured so we can later add Notion journal writing, news summaries, and more tickers.

Current features:

- MA5
- MA20
- MA50
- MA200
- RSI14
- MACD line, signal, and histogram
- ATR14
- DeepSeek-generated trading report with fallback behavior
- Markdown report output under `report/markdown/YYYY-MM-DD_TICKER_premarket.md`
- Single-ticker HTML output under `report/html/YYYY-MM-DD_TICKER_premarket.html`
- Multi-ticker HTML output under `report/html/YYYY-MM-DD_COST_MSFT_premarket.html` with a symbol dropdown
- Latest HTML duplicate output under `report/StockReportAnalysisToday.html`
- Gmail delivery with `StockReportAnalysisToday.html` attached
- GitHub Actions scheduled automation and manual dispatch support
- Gmail API email delivery

## Requirements

- Python 3.11
- Internet access for `yfinance` to download price history
- `DEEPSEEK_API_KEY` for AI-generated reports
- Optional: `DEEPSEEK_MODEL` to override the default model name
- `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, `GMAIL_SENDER`, and `EMAIL_TO` for Gmail API email delivery
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
- `REPORT_TICKER` if you want to choose symbols. Use `COST`, `MSFT`, `COST,MSFT`, or `ALL`
- `REPORT_TYPE` if you want to override the default `premarket`
- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REFRESH_TOKEN`
- `GMAIL_SENDER`
- `EMAIL_TO`
- `OPENAI_API_KEY` and `OPENAI_MODEL` if you want an OpenAI backup path
- `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, `GMAIL_SENDER`, and `EMAIL_TO` if you want email delivery

## Run locally

From the project root:

```bash
python src/main.py
```

You can also use `python -m src.main` if you prefer module execution.

That will fetch at least one year of daily data for the selected ticker or ticker list, calculate indicators, generate the DeepSeek report, and save output under `report/`. Markdown files are saved per ticker under `report/markdown/`. HTML files are saved under `report/html/`. Every run also refreshes `report/StockReportAnalysisToday.html` with the newest HTML report. When multiple tickers are selected, HTML is saved as one combined dropdown page instead of separate HTML files. If DeepSeek is unavailable, the program tries OpenAI when `OPENAI_API_KEY` is set. If both fail or are missing, it falls back to a rule-based Chinese report.

Examples:

```bash
REPORT_TICKER=COST python src/main.py
REPORT_TICKER=MSFT python src/main.py
REPORT_TICKER=COST,MSFT python src/main.py
REPORT_TICKER=ALL python src/main.py
```

The HTML version uses a card-based layout inspired by the provided design. Multi-ticker runs reuse the already generated report text and do not make extra DeepSeek calls just to build the combined HTML page.

If Gmail settings are present, the app also sends the generated report as a plain-text email. If email sending fails, the Markdown file is still kept and the program continues.

## GitHub Actions

The workflow file is `.github/workflows/daily_report.yml`.

It runs automatically Monday through Friday at `4:30 PM America/Toronto` using GitHub's timezone-aware schedule.

### GitHub Secrets

Add these secrets in your repository settings:

- `DEEPSEEK_API_KEY`
- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REFRESH_TOKEN`
- `GMAIL_SENDER`
- `EMAIL_TO`

If Gmail secrets are missing, the workflow still generates report files and skips email delivery.

Optional repository variables or workflow env values:

- `DEEPSEEK_MODEL` defaults to `deepseek-v4-flash`
- `REPORT_TICKER` defaults to `ALL` in GitHub Actions and generates every configured ticker
- `REPORT_TYPE` defaults to `premarket`

### Manual trigger

Use the `workflow_dispatch` button in GitHub Actions and provide:

- `ticker` defaults to `ALL`
- `ticker` accepts `COST`, `MSFT`, `COST,MSFT`, or `ALL`
- `report_type` defaults to `premarket`

The workflow installs dependencies, runs `python src/main.py`, sends the latest HTML report by Gmail when Gmail secrets are configured, and uploads generated Markdown and HTML files from `report/` as artifacts.

## Gmail Setup

1. Create or choose a Google Cloud project.
2. Enable the Gmail API for that project.
3. Configure an OAuth consent screen and create an OAuth client for a desktop app or installed app flow.
4. Generate a refresh token for the account that will send mail.
5. Put the values in your local `.env` file or GitHub Secrets:
   - `GMAIL_CLIENT_ID`
   - `GMAIL_CLIENT_SECRET`
   - `GMAIL_REFRESH_TOKEN`
   - `GMAIL_SENDER`
   - `EMAIL_TO`

The app uses the refresh token flow to obtain a short-lived access token, then calls the Gmail API `users.messages.send` endpoint with a plain-text message.

## Notes

- Generated reports are not committed automatically.
- Notion and news summaries will come in later phases.
