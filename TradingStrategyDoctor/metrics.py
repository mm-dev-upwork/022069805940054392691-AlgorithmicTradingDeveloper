"""
Trading Strategy Doctor — Metrics Module
=========================================
Computation of professional trading metrics.
All functions are pure, deterministic, and operate on a filtered DataFrame.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from analysis import detect_schema


# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------

def compute_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """
    Calculate the full set of trading metrics from a trades DataFrame.
    Returns a flat dict with camelCase keys for the front-end.
    """
    col_map = detect_schema(df)
    rev: dict[str, str] = {c.canonical: csv for csv, c in col_map.items()}

    net_pnl_col = rev.get("NetPnl", "NetPnl")
    gross_pnl_col = rev.get("Pnl", "Pnl")

    if df.empty:
        return _empty_metrics()

    # Net Profit — sum of NetPnl
    net_profit = float(df[net_pnl_col].sum())

    # Total Trades
    total_trades = len(df)

    # Winners / Losers
    winners = df[df[net_pnl_col] > 0]
    losers  = df[df[net_pnl_col] < 0]
    win_count = len(winners)
    loss_count = len(losers)

    # Win Rate
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0

    # Profit Factor
    gross_profit = winners[gross_pnl_col].sum() if win_count > 0 else 0.0
    gross_loss   = abs(losers[gross_pnl_col].sum()) if loss_count > 0 else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else 0.0
    )

    # Average Winner / Loser
    avg_winner = float(winners[net_pnl_col].mean()) if win_count > 0 else 0.0
    avg_loser  = float(abs(losers[net_pnl_col].mean())) if loss_count > 0 else 0.0

    # Average Risk-Reward (absolute ratio)
    avg_rr = avg_winner / avg_loser if avg_loser > 0 else 0.0

    # Maximum Drawdown — computed from equity curve
    max_drawdown, _max_dd_pct = _compute_max_drawdown(df, net_pnl_col)

    # Trade Duration (vectorised — pre-computed in analysis.py)
    if "_DurationMin" in df.columns:
        dur_vals = df["_DurationMin"]
        avg_duration = float(dur_vals.mean()) if len(dur_vals) > 0 else 0.0
    else:
        avg_duration = 0.0

    # MFE / MAE
    mfe_col = rev.get("Mfe")
    mae_col = rev.get("Mae")
    avg_mfe = float(df[mfe_col].mean()) if mfe_col and mfe_col in df.columns else 0.0
    avg_mae = float(df[mae_col].mean()) if mae_col and mae_col in df.columns else 0.0

    # Largest Winner / Loser
    largest_winner = float(df[net_pnl_col].max()) if total_trades > 0 else 0.0
    largest_loser  = float(df[net_pnl_col].min()) if total_trades > 0 else 0.0

    return {
        "netProfit":       _round(net_profit, 2),
        "totalTrades":     total_trades,
        "winRate":         _round(win_rate, 1),
        "profitFactor":    _round(profit_factor, 2) if profit_factor != float("inf") else "∞",
        "avgWinner":       _round(avg_winner, 2),
        "avgLoser":        _round(avg_loser, 2),
        "avgRR":           _round(avg_rr, 2),
        "maxDrawdown":     _round(max_drawdown, 2),
        "avgTradeDuration": _round(avg_duration, 1),
        "avgMfe":          _round(avg_mfe, 2),
        "avgMae":          _round(avg_mae, 2),
        "largestWinner":   _round(largest_winner, 2),
        "largestLoser":    _round(largest_loser, 2),
        # Derived helpers for the rule engine
        "totalTrades":     total_trades,
        "winCount":        win_count,
        "lossCount":       loss_count,
        "grossProfit":     _round(gross_profit, 2),
        "grossLoss":       _round(gross_loss, 2),
    }


def _empty_metrics() -> dict[str, Any]:
    """Return zeroed-out metrics for an empty DataFrame."""
    return {
        "netProfit": 0.0, "totalTrades": 0, "winRate": 0.0,
        "profitFactor": 0.0, "avgWinner": 0.0, "avgLoser": 0.0,
        "avgRR": 0.0, "maxDrawdown": 0.0, "avgTradeDuration": 0.0,
        "avgMfe": 0.0, "avgMae": 0.0, "largestWinner": 0.0,
        "largestLoser": 0.0,
        "winCount": 0, "lossCount": 0, "grossProfit": 0.0, "grossLoss": 0.0,
    }


def _round(val: float, decimals: int) -> float:
    """Safely round, handling inf/nan."""
    if val in (float("inf"), float("-inf"), float("nan")):
        return 0.0
    return round(val, decimals)


# ---------------------------------------------------------------------------
# Drawdown
# ---------------------------------------------------------------------------

def _compute_max_drawdown(df: pd.DataFrame, pnl_col: str) -> tuple[float, float]:
    """
    Return (max_drawdown_absolute, max_drawdown_percent) based on the
    cumulative PnL equity curve.
    """
    if df.empty:
        return 0.0, 0.0

    equity = df[pnl_col].cumsum().values
    peak = np.maximum.accumulate(equity)
    dd = peak - equity
    max_dd = float(np.max(dd))
    dd_pct = float(np.max(dd / (peak + 1e-12))) * 100
    return max_dd, dd_pct

# ---------------------------------------------------------------------------
# Series data for charts
# ---------------------------------------------------------------------------

def compute_equity_curve(df: pd.DataFrame, max_points: int = 500) -> list[dict[str, Any]]:
    """
    Return a list of {date, equity} points sorted chronologically.
    Downsampled to *max_points* for chart performance.
    """
    col_map = detect_schema(df)
    rev: dict[str, str] = {c.canonical: csv for csv, c in col_map.items()}
    pnl_col = rev.get("NetPnl", "NetPnl")
    date_col = rev.get("Date")

    if df.empty or date_col is None:
        return [{"date": "N/A", "equity": 0.0}]

    sorted_df = df.sort_values(date_col)
    sorted_df["_eq"] = sorted_df[pnl_col].cumsum()

    # Downsample for chart performance
    if len(sorted_df) > max_points:
        idx = np.linspace(0, len(sorted_df) - 1, max_points, dtype=int)
        sorted_df = sorted_df.iloc[idx]

    dates = sorted_df[date_col].dt.strftime("%Y-%m-%d")
    eqs = sorted_df["_eq"].round(2).values
    return [{"date": d, "equity": float(e)} for d, e in zip(dates, eqs)]


def compute_monthly_pnl(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return a list of {month, pnl} for the monthly profit bar chart."""
    col_map = detect_schema(df)
    rev: dict[str, str] = {c.canonical: csv for csv, c in col_map.items()}
    pnl_col = rev.get("NetPnl", "NetPnl")
    date_col = rev.get("Date")

    if df.empty or date_col is None:
        return [{"month": "N/A", "pnl": 0.0}]

    df = df.copy()
    df["_month"] = df[date_col].dt.to_period("M").astype(str)
    grouped = df.groupby("_month")[pnl_col].sum().reset_index()
    grouped.columns = ["month", "pnl"]
    return grouped.to_dict("records")


def compute_pnl_distribution(df: pd.DataFrame, bins: int = 20) -> list[dict[str, Any]]:
    """Return histogram bins (count per PnL bucket) for the distribution chart."""
    col_map = detect_schema(df)
    rev: dict[str, str] = {c.canonical: csv for csv, c in col_map.items()}
    pnl_col = rev.get("NetPnl", "NetPnl")

    if df.empty:
        return [{"binStart": 0, "binEnd": 0, "count": 0}]

    values = df[pnl_col].values
    counts, edges = np.histogram(values, bins=bins)
    return [{
        "binStart": _round(float(edges[i]), 2),
        "binEnd":   _round(float(edges[i + 1]), 2),
        "count":    int(counts[i]),
    } for i in range(len(counts))]


def compute_drawdown_series(df: pd.DataFrame, max_points: int = 500) -> list[dict[str, Any]]:
    """Return drawdown series (date, drawdown%) for the drawdown area chart, downsampled."""
    col_map = detect_schema(df)
    rev: dict[str, str] = {c.canonical: csv for csv, c in col_map.items()}
    pnl_col = rev.get("NetPnl", "NetPnl")
    date_col = rev.get("Date")

    if df.empty or date_col is None:
        return [{"date": "N/A", "drawdown": 0.0}]

    sorted_df = df.sort_values(date_col).reset_index(drop=True)
    equity = sorted_df[pnl_col].cumsum().values
    peak = np.maximum.accumulate(equity)
    dd_pct = ((peak - equity) / (peak + 1e-12)) * 100

    # Downsample
    n = len(sorted_df)
    if n > max_points:
        idx = np.linspace(0, n - 1, max_points, dtype=int)
        sorted_df = sorted_df.iloc[idx]
        dd_pct = dd_pct[idx]

    dates = sorted_df[date_col].dt.strftime("%Y-%m-%d")
    return [{"date": d, "drawdown": round(float(p), 2)} for d, p in zip(dates, dd_pct)]


def compute_duration_histogram(df: pd.DataFrame, bins: int = 15) -> list[dict[str, Any]]:
    """Return histogram of trade durations (minutes) for the duration chart."""
    if "_DurationMin" in df.columns:
        durations = df["_DurationMin"].values
        durations = durations[durations > 0]
    else:
        durations = np.array([])

    if len(durations) == 0:
        return [{"binStart": 0, "binEnd": 0, "count": 0}]

    counts, edges = np.histogram(durations, bins=bins)
    result = []
    for i in range(len(counts)):
        result.append({
            "binStart": _round(float(edges[i]), 1),
            "binEnd":   _round(float(edges[i + 1]), 1),
            "count":    int(counts[i]),
        })
    return result


def compute_win_loss_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Return counts for the win/loss doughnut chart."""
    col_map = detect_schema(df)
    rev: dict[str, str] = {c.canonical: csv for csv, c in col_map.items()}
    pnl_col = rev.get("NetPnl", "NetPnl")

    wins = int((df[pnl_col] > 0).sum())
    losses = int((df[pnl_col] < 0).sum())
    return {"wins": wins, "losses": losses}
