# Trading Strategy Doctor

A professional, lightweight quantitative research dashboard for reviewing and improving algorithmic trading strategies. Built as an internal tool for trading firms — no AI, no databases, purely deterministic calculations.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)
![Chart.js](https://img.shields.io/badge/Chart.js-4.4-orange)

---

## Features

- **CSV Upload** — Drag-and-drop or browse. Auto-detects schema from your trade file. Falls back to built-in sample data.
- **Strategy-Level Analytics** — Filter by Symbol, StrategyName, Session, TimeFrame, StateMachine, ExitReason, and Date Range.
- **13 Professional Metrics** — Net Profit, Win Rate, Profit Factor, Average R:R, Max Drawdown, MFE/MAE, Trade Duration, and more — each with an info icon explaining its meaning and thresholds.
- **6 Interactive Charts** — Equity Curve, PnL Distribution, Monthly Profit, Win vs Loss (doughnut), Drawdown Curve, Trade Duration Histogram.
- **Strategy Health Score (0–100)** — Colour-coded (green / yellow / red) with a deterministic rule engine that scores based on Profit Factor, Win Rate, R:R, Drawdown, and sample size.
- **Strategy Diagnosis** — Automatically generated Strengths, Weaknesses, Risks, and Recommendations based on quantitative rules.
- **Trade Table** — Searchable, sortable, paginated Bootstrap table. Green for winners, red for losers.
- **Export Report** — Download a printable HTML report with all metrics and diagnosis.
- **Dark / Light Theme** — TradingView-inspired. Light by default, toggle persists in localStorage.
- **Fully Local** — No database, no cloud, no API keys. Everything runs on your machine.

---

## Installation

### Prerequisites

- Python 3.12+
- pip

### Setup

```bash
# 1. Clone or copy the project
cd TradingStrategyDoctor

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
uvicorn app:app --reload
```

### Usage

1. Open `http://localhost:8000` in your browser.
2. Drag & drop your trade CSV or click **Load Sample Data** to explore with the built-in sample.
3. Use the filter bar to slice by Symbol, Strategy, Session, etc.
4. Review metric cards, charts, health score, and diagnosis.
5. Export a report with the **Export Report** button.

---

## CSV Format

The app expects columns similar to the following (based on `SampleInput.csv`). Only **Symbol**, **Date**, **Pnl**, and **NetPnl** are required — all others are optional.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| Symbol | String | Yes | Ticker symbol |
| Date | Integer (YYYYMMDD) | Yes | Trade date |
| Session | String | No | Trading session (Utc, Ist, Est, …) |
| TimeFrame | Integer/String | No | Chart timeframe in minutes |
| StrategyName | String | No | Strategy identifier |
| StateMachine | String | No | State machine type |
| EntryNumber | Integer | No | Entry number within the trade |
| OrderId | String | No | Unique order ID |
| Quantity | Float | No | Trade quantity |
| EntryFillPrice | Float | No | Entry fill price |
| EntryAmount | Float | No | Entry notional amount |
| EntryFillTime | String | No | Entry time (HH:MM:SS) |
| ExitFillPrice | Float | No | Exit fill price |
| ExitAmount | Float | No | Exit notional amount |
| ExitFillTime | String | No | Exit time (HH:MM:SS) |
| ExitReason | String | No | Reason for exit |
| Pnl | Float | Yes | Gross PnL |
| PnlPerc | Float | No | PnL as percentage |
| NetPnl | Float | Yes | Net PnL (after costs) |
| Mfe | Float | No | Max Favorable Excursion |
| MfePerc | Float | No | MFE as percentage |
| MfeTimeStamp | String | No | Time of MFE |
| Mae | Float | No | Max Adverse Excursion |
| MaePerc | Float | No | MAE as percentage |
| MaeTimeStamp | String | No | Time of MAE |

Unknown columns are silently ignored. Missing required columns show a user-friendly error message.

---

## Project Structure

```
TradingStrategyDoctor/
├── app.py                  # FastAPI application — routes, session management
├── analysis.py             # CSV schema detection, validation, parsing, filtering
├── metrics.py              # Trading metrics computation (PnL, drawdown, durations, etc.)
├── rules.py                # Deterministic rule engine, health score, diagnosis
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── sample_data/
│   └── sample_trades.csv   # Built-in sample trade data
├── templates/
│   ├── index.html          # Upload page with drag-drop
│   ├── dashboard.html      # Full dashboard template
│   └── report.html         # Export report template
└── static/
    ├── css/
    │   └── style.css       # TradingView-inspired, light/dark theme
    └── js/
        ├── charts.js       # Chart.js 6-chart initialisation & updates
        └── dashboard.js    # Filters, metrics, table, health, export, theme
```

---

## Architecture

```
[Upload CSV] → analysis.py (parse/validate) → metrics.py (compute) → [JSON API]
                                                      ↓
                                              rules.py (health + diagnosis)
                                                      ↓
                                         templates (Jinja2 + Chart.js)
```

- **Backend**: FastAPI with in-memory DataFrame store (no database).
- **Frontend**: Jinja2 templates, Bootstrap 5, Chart.js, vanilla JavaScript.
- **Design**: Clean separation — `analysis.py` handles data, `metrics.py` computes, `rules.py` evaluates. Adding new metrics or rules requires minimal code changes.

---

## Metrics Explained

| Metric | Formula | Good | Excellent |
|--------|---------|------|-----------|
| Profit Factor | Gross Profit / Gross Loss | > 1.5 | > 2.0 |
| Win Rate | Winners / Total Trades × 100 | > 55% | > 65% |
| Avg R:R | Avg Winner / Avg Loser | > 1.5 | > 2.0 |
| Max Drawdown | Peak-to-trough decline | < 10% | < 5% |

---

## Screenshots

*[Screenshots to be added — see the live dashboard at http://localhost:8000]*

---

## Future Improvements

- Multi-file comparison (compare two strategy runs side-by-side)
- Monte Carlo simulation for equity curve confidence intervals
- Rolling metrics (rolling win rate, rolling Sharpe)
- Custom rule configuration via UI
- Sharpe Ratio, Sortino Ratio, Calmar Ratio
- Trade journaling with notes/tags
- Automated stop-loss / take-profit suggestions based on MFE/MAE analysis

---

## License

MIT — use freely for personal or commercial projects.
