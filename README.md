<div align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Pandas-3.0-150458?style=flat&logo=pandas&logoColor=white" alt="Pandas">
  <img src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=flat&logo=bootstrap&logoColor=white" alt="Bootstrap">
  <img src="https://img.shields.io/badge/Chart.js-4.4-FF6384?style=flat&logo=chartdotjs&logoColor=white" alt="Chart.js">
  <br>
  <img src="https://img.shields.io/badge/License-Proprietary-red?style=flat" alt="License">
  <img src="https://img.shields.io/badge/Status-Production_Ready-success?style=flat" alt="Status">
</div>

<br>

<div align="center">
  <h1>📈 Trading Strategy Doctor</h1>
  <p><strong>A professional quantitative research dashboard for reviewing and improving algorithmic trading strategies.</strong></p>
  <p>Built as an internal tool for trading firms — no AI, no databases, purely deterministic calculations.</p>
  <p>
    <a href="https://zero22069805940054392691.onrender.com/">🌐 Live Demo</a>
  </p>
</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **CSV Upload** | Drag-and-drop or browse. Auto-detects schema from your trade file. Falls back to built-in sample data. |
| **Strategy-Level Analytics** | Filter by Symbol, StrategyName, Session, TimeFrame, StateMachine, ExitReason, and Date Range. |
| **13 Professional Metrics** | Net Profit, Win Rate, Profit Factor, Average R:R, Max Drawdown, MFE/MAE, Trade Duration, Largest Winner/Loser — each with info icon and threshold explanations. |
| **6 Interactive Charts** | Equity Curve, PnL Distribution, Monthly Profit, Win vs Loss (doughnut), Drawdown Curve, Trade Duration Histogram. Built with Chart.js. |
| **Strategy Health Score (0–100)** | Colour-coded (green / yellow / red). Deterministic rule engine scores based on Profit Factor, Win Rate, R:R, Drawdown, sample size, and more. |
| **Strategy Diagnosis** | Auto-generated Strengths, Weaknesses, Risks, and Recommendations — all rule-based, no AI. |
| **Trade Table** | Searchable, sortable, paginated. Green for winners, red for losers. |
| **Export Report** | Download a self-contained printable HTML report with all metrics and diagnosis. |
| **Dark / Light Theme** | TradingView-inspired. Light by default, toggle persists in localStorage. |
| **Fully Local** | No database, no cloud, no API keys. Everything runs on your machine. |

---

## 🛠 Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **Python 3.12+** | Core language |
| **FastAPI** | REST API framework |
| **Pandas** | Data manipulation and analysis |
| **NumPy** | Numerical operations |
| **Gunicorn + Uvicorn** | Production ASGI server |

### Frontend
| Technology | Purpose |
|------------|---------|
| **Jinja2 Templates** | Server-side HTML rendering |
| **Bootstrap 5** | Responsive UI framework |
| **Chart.js** | Interactive charts |
| **Vanilla JavaScript** | Client-side logic — no frameworks |

No React, no TypeScript, no Tailwind, no databases.

---

## 📦 Installation

### Prerequisites
- Python 3.12+
- pip

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/TradingStrategyDoctor.git
cd TradingStrategyDoctor

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app:app --reload
```

Open **http://localhost:8000** in your browser.

### Dashboard with Sample Data

No CSV to test with? The app **automatically loads sample data** at startup. Just start the server and open the dashboard:

```bash
uvicorn app:app --reload
# Open http://localhost:8000/dashboard
```

The sample dashboard will display all metrics, charts, health score, and diagnosis immediately — no upload needed. Use the filter bar to explore by Symbol, Strategy, Session, or TimeFrame.

> **💡 On the live demo:** Visit the [Live Demo](https://zero22069805940054392691.onrender.com/), then click **"Or load sample data"** on the upload page to explore the dashboard immediately with built-in sample trades.

---

## 📄 Sample CSV Format

The app is designed around the schema in `sample_data/sample_trades.csv`. Only **Symbol**, **Date**, **Pnl**, and **NetPnl** are required — everything else is optional.

```csv
Symbol,Date,Session,TimeFrame,StrategyName,StateMachine,EntryNumber,OrderId,Quantity,EntryFillPrice,EntryAmount,EntryFillTime,ExitFillPrice,ExitAmount,ExitFillTime,ExitReason,Pnl,PnlPerc,NetPnl,Mfe,MfePerc,MfeTimeStamp,Mae,MaePerc,MaeTimeStamp
ADAUSDT,20240102,Utc,5,VolumeAbsorption,Breakout,1,f95a89d0...,16,0.6228,9.9648,00:04:00,0.629,10.064,00:22:00,FixedPercentEod,0.0062,0.9955,0.0992,0.629,0.9955,22:00.0,0.6222,-0.0963,15:00.0
```

### Required Columns

| Column | Type | Description |
|--------|------|-------------|
| Symbol | String | Ticker symbol (e.g. BTCUSDT, ETHUSDT) |
| Date | Integer (YYYYMMDD) | Trade date |
| Pnl | Float | Gross PnL |
| NetPnl | Float | Net PnL after costs |

### Optional Columns (app uses if present)

Session, TimeFrame, StrategyName, StateMachine, EntryNumber, OrderId, Quantity, EntryFillPrice, EntryAmount, EntryFillTime, ExitFillPrice, ExitAmount, ExitFillTime, ExitReason, PnlPerc, Mfe, MfePerc, MfeTimeStamp, Mae, MaePerc, MaeTimeStamp

Unknown columns are silently ignored. Missing required columns show a friendly error message.

---

## 📊 Example Dashboard

When you load the sample data or upload your own CSV, the dashboard displays:

### Metric Cards
Top-row cards showing key performance indicators at a glance:

```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ NET PROFIT  │ │ TOTAL TRADES│ │  WIN RATE   │ │PROFIT FACTOR│
│   $1,234    │ │     51      │ │   25.5%     │ │    0.40     │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### Charts
6 interactive Chart.js visualizations arranged in a responsive grid.

### Strategy Health Score
A prominent score out of 100 with color coding:
- **≥ 70** 🟢 Good
- **40–69** 🟡 Fair
- **< 40** 🔴 Poor

### Strategy Diagnosis
Four sections: Strengths, Weaknesses, Risks, Recommendations — auto-generated from quantitative rules.

### Trade Log
Full searchable, sortable, paginated table with color-coded rows.

---

## 🏗 Project Structure

```
TradingStrategyDoctor/
├── app.py                  # FastAPI application — routes, session management
├── analysis.py             # CSV schema detection, validation, parsing, filtering
├── metrics.py              # Trading metrics computation (PnL, drawdown, durations, etc.)
├── rules.py                # Deterministic rule engine, health score, diagnosis
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment config
├── README.md               # This file
├── sample_data/
│   └── sample_trades.csv   # Built-in sample trade data (48 trades)
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

## 🔧 Architecture

```
[Upload CSV] → analysis.py (parse/validate) → metrics.py (compute) → [JSON API]
                                                      ↓
                                              rules.py (health + diagnosis)
                                                      ↓
                                         templates (Jinja2 + Chart.js)
```

- **Backend**: FastAPI with in-memory DataFrame store — no database.
- **Frontend**: Jinja2 server-side templates, Bootstrap 5, Chart.js, vanilla JS.
- **Design**: Clean separation of concerns. Adding new metrics or rules requires minimal code changes.

---

## 🧮 Metrics Explained

| Metric | Formula | Good | Excellent |
|--------|---------|------|-----------|
| Profit Factor | Gross Profit / Gross Loss | > 1.5 | > 2.0 |
| Win Rate | Winners / Total Trades × 100 | > 55% | > 65% |
| Avg R:R | Avg Winner / Avg Loser | > 1.5 | > 2.0 |
| Max Drawdown | Peak-to-trough decline | < 10% | < 5% |
| Avg Trade Duration | Mean holding period | — | — |
| MFE | Max Favorable Excursion | — | — |
| MAE | Max Adverse Excursion | — | — |

---

## 🗺 Future Roadmap

| Feature | Priority | Description |
|---------|----------|-------------|
| Multi-file comparison | Medium | Compare two strategy runs side-by-side |
| Monte Carlo simulation | Low | Equity curve confidence intervals |
| Rolling metrics | Low | Rolling win rate, rolling Sharpe |
| Custom rule configuration | Medium | User-defined rules via UI |
| Sharpe / Sortino / Calmar | Low | Additional risk-adjusted return metrics |
| Trade journaling | Low | Notes and tags on individual trades |
| Stop-loss suggestions | Medium | Based on MFE/MAE distribution analysis |

---

## 🚀 Deployment

This app is deployed on **Render.com**:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Settings
| Setting | Value |
|---------|-------|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app` |
| Root Directory | `TradingStrategyDoctor` |

---

## 📝 License

Proprietary — All rights reserved. See [LICENSE](LICENSE) for terms and conditions.

---

<div align="center">
  <sub>Built for quantitative traders who care about correctness, not flash.</sub>
</div>
