"""
Trading Strategy Doctor — Analysis Module
==========================================
CSV schema detection, validation, parsing, and filtering layer.
All logic is deterministic and rule-based, not AI-driven.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Schema definitions — one source of truth for column handling
# ---------------------------------------------------------------------------

@dataclass
class ColumnDef:
    """Descriptor for a known column in the trade CSV."""
    canonical: str          # Normalised internal name
    required: bool = False  # Must be present for the app to function
    dtype: str = "float"    # Target pandas dtype: float, int, str, datetime
    description: str = ""


# The reference schema, built from SampleInput.csv.
# Keys are lowercase, space-/hyphen-stripped matchers so the app is
# forgiving about slight variations in column naming (e.g. "PnL" vs "pnl").
COLUMN_DEFS: dict[str, ColumnDef] = {
    "symbol":        ColumnDef("Symbol",        required=True,  dtype="str",     description="Ticker symbol"),
    "date":          ColumnDef("Date",          required=True,  dtype="datetime", description="Trade date (YYYYMMDD or parseable)"),
    "session":       ColumnDef("Session",       required=False, dtype="str",     description="Trading session (Utc, Ist, Est…)"),
    "timeframe":     ColumnDef("TimeFrame",     required=False, dtype="str",     description="Chart timeframe (5, 15, 30, 60, 240…)"),
    "strategyname":  ColumnDef("StrategyName",  required=False, dtype="str",     description="Strategy identifier"),
    "statemachine":  ColumnDef("StateMachine",  required=False, dtype="str",     description="State-machine type"),
    "entrynumber":   ColumnDef("EntryNumber",   required=False, dtype="int",     description="Entry number within the trade"),
    "orderid":       ColumnDef("OrderId",       required=False, dtype="str",     description="Unique order identifier"),
    "quantity":      ColumnDef("Quantity",      required=False, dtype="float",   description="Trade quantity in base units"),
    "entryfillprice":  ColumnDef("EntryFillPrice",  required=False, dtype="float",  description="Entry fill price"),
    "entryamount":     ColumnDef("EntryAmount",     required=False, dtype="float",  description="Entry notional amount"),
    "entryfilltime":   ColumnDef("EntryFillTime",   required=False, dtype="str",   description="Entry fill time (HH:MM:SS)"),
    "exitfillprice":   ColumnDef("ExitFillPrice",   required=False, dtype="float",  description="Exit fill price"),
    "exitamount":      ColumnDef("ExitAmount",      required=False, dtype="float",  description="Exit notional amount"),
    "exitfilltime":    ColumnDef("ExitFillTime",    required=False, dtype="str",   description="Exit fill time (HH:MM:SS)"),
    "exitreason":      ColumnDef("ExitReason",      required=False, dtype="str",   description="Reason for exit"),
    "pnl":           ColumnDef("Pnl",           required=True,  dtype="float",   description="Gross PnL"),
    "pnlperc":       ColumnDef("PnlPerc",       required=False, dtype="float",   description="PnL as percentage"),
    "netpnl":        ColumnDef("NetPnl",        required=True,  dtype="float",   description="Net PnL (after costs)"),
    "mfe":           ColumnDef("Mfe",           required=False, dtype="float",   description="Maximum Favorable Excursion"),
    "mfeperc":       ColumnDef("MfePerc",       required=False, dtype="float",   description="MFE as percentage"),
    "mfetimestamp":  ColumnDef("MfeTimeStamp",  required=False, dtype="str",     description="Time of MFE (HH:MM:SS.S)"),
    "mae":           ColumnDef("Mae",           required=False, dtype="float",   description="Maximum Adverse Excursion"),
    "maeperc":       ColumnDef("MaePerc",       required=False, dtype="float",   description="MAE as percentage"),
    "maetimestamp":  ColumnDef("MaeTimeStamp",  required=False, dtype="str",     description="Time of MAE (HH:MM:SS.S)"),
}


# ---------------------------------------------------------------------------
# Schema detection
# ---------------------------------------------------------------------------

def _normalise(name: str) -> str:
    """Strip whitespace, hyphens, underscores and lower-case for fuzzy matching."""
    return name.strip().replace("-", "").replace("_", "").replace(" ", "").lower()


def detect_schema(df: pd.DataFrame) -> dict[str, ColumnDef]:
    """
    Build a mapping from actual CSV column → ColumnDef.

    Unknown columns are silently ignored.  Missing *required* columns will
    be caught by `validate_columns`.
    """
    col_map: dict[str, ColumnDef] = {}
    for csv_col in df.columns:
        key = _normalise(csv_col)
        if key in COLUMN_DEFS:
            col_map[csv_col] = COLUMN_DEFS[key]
    return col_map


def validate_columns(df: pd.DataFrame) -> list[str]:
    """
    Return a list of user-friendly error messages for missing required
    columns.  Empty list means the CSV is valid.
    """
    col_map = detect_schema(df)
    found_canonicals = {c.canonical for c in col_map.values()}
    errors: list[str] = []
    for col in COLUMN_DEFS.values():
        if col.required and col.canonical not in found_canonicals:
            errors.append(f"Missing required column: '{col.canonical}'. {col.description}.")
    return errors


# ---------------------------------------------------------------------------
# Parsing / type coercion
# ---------------------------------------------------------------------------

def parse_trades(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise types on a DataFrame whose columns have already been
    mapped via `detect_schema` / `validate_columns`.

    * Date → datetime
    * Numeric columns → float (int for EntryNumber)
    * Missing optional numeric columns → 0.0 / 0
    * Pre-compute trade duration as vectorised column '_DurationMin'.

    Modifies the DataFrame in place and returns it for chaining.
    """
    col_map = detect_schema(df)

    for csv_col, coldef in col_map.items():
        if coldef.dtype == "datetime":
            df[csv_col] = pd.to_datetime(df[csv_col], format="%Y%m%d", errors="coerce")
        elif coldef.dtype == "float":
            df[csv_col] = pd.to_numeric(df[csv_col], errors="coerce").fillna(0.0)
        elif coldef.dtype == "int":
            df[csv_col] = pd.to_numeric(df[csv_col], errors="coerce").fillna(0).astype(int)
        elif coldef.dtype == "str":
            df[csv_col] = df[csv_col].astype(str)

    # Vectorised trade duration (avoids slow row-by-row loops)
    _vectorise_duration(df, col_map)

    return df


def _vectorise_duration(df: pd.DataFrame, col_map: dict) -> None:
    """Add '_DurationMin' column using vectorised operations."""
    rev: dict[str, str] = {c.canonical: csv for csv, c in col_map.items()}
    entry_csv = rev.get("EntryFillTime")
    exit_csv = rev.get("ExitFillTime")
    if entry_csv is None or exit_csv is None:
        df["_DurationMin"] = 0.0
        return
    if entry_csv not in df.columns or exit_csv not in df.columns:
        df["_DurationMin"] = 0.0
        return

    # Parse HH:MM:SS to total seconds
    def _to_seconds(ser: pd.Series) -> pd.Series:
        parts = ser.str.extract(r"(\d+):(\d+):([\d.]+)", expand=True)
        parts = parts.fillna("0")
        h = parts[0].astype(float)
        m = parts[1].astype(float)
        s = parts[2].astype(float)
        return h * 3600 + m * 60 + s

    entry_sec = _to_seconds(df[entry_csv].astype(str))
    exit_sec = _to_seconds(df[exit_csv].astype(str))

    # Handle overnight: if exit < entry presume +24 h
    mask_neg = exit_sec < entry_sec
    exit_sec = exit_sec.where(~mask_neg, exit_sec + 86400)

    df["_DurationMin"] = ((exit_sec - entry_sec) / 60.0).fillna(0.0)


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

@dataclass
class Filters:
    """User-selected filter values.  None / empty = no restriction."""
    symbols:      list[str] = field(default_factory=list)
    strategies:   list[str] = field(default_factory=list)
    sessions:     list[str] = field(default_factory=list)
    timeframes:   list[str] = field(default_factory=list)
    state_machines: list[str] = field(default_factory=list)
    exit_reasons: list[str] = field(default_factory=list)
    date_from:    Optional[date] = None
    date_to:      Optional[date] = None


def apply_filters(df: pd.DataFrame, filters: Filters) -> pd.DataFrame:
    """
    Return a filtered copy of the trades DataFrame.
    All filter dimensions use an OR-within, AND-across strategy.
    """
    col_map = detect_schema(df)
    # Build reverse lookup: canonical → csv_column
    rev: dict[str, str] = {c.canonical: csv for csv, c in col_map.items()}

    mask = pd.Series(True, index=df.index)

    def _in(col_canonical: str, values: list[str]) -> pd.Series:
        csv = rev.get(col_canonical)
        if csv is None or not values:
            return pd.Series(True, index=df.index)
        return df[csv].astype(str).isin(values)

    mask &= _in("Symbol", filters.symbols)
    mask &= _in("StrategyName", filters.strategies)
    mask &= _in("Session", filters.sessions)
    mask &= _in("TimeFrame", filters.timeframes)
    mask &= _in("StateMachine", filters.state_machines)
    mask &= _in("ExitReason", filters.exit_reasons)

    # Date range
    date_col = rev.get("Date")
    if date_col is not None:
        if filters.date_from is not None:
            mask &= df[date_col].dt.date >= filters.date_from
        if filters.date_to is not None:
            mask &= df[date_col].dt.date <= filters.date_to

    return df.loc[mask].reset_index(drop=True)


def get_filter_options(df: pd.DataFrame) -> dict[str, list[str]]:
    """
    Return unique values for each filterable dimension.
    Sorted alphabetically and coerced to strings.
    """
    col_map = detect_schema(df)
    options: dict[str, list[str]] = {}
    for canon in ("Symbol", "StrategyName", "Session", "TimeFrame",
                   "StateMachine", "ExitReason"):
        csv = next((c for c, d in col_map.items() if d.canonical == canon), None)
        if csv is not None and csv in df.columns:
            vals = sorted(str(v) for v in df[csv].unique() if str(v) not in ("", "nan", "<NA>"))
            options[canon] = vals
    return options


# ---------------------------------------------------------------------------
# Trade duration helper
# ---------------------------------------------------------------------------

def compute_trade_duration_minutes(row: pd.Series, col_map: dict) -> float:
    """
    Compute trade duration in minutes from EntryFillTime / ExitFillTime.
    Both are expected as "HH:MM:SS" strings.  Returns 0.0 if either is missing.
    Kept for backward-compatibility; prefer the vectorised '_DurationMin' column.
    """
    rev: dict[str, str] = {c.canonical: csv for csv, c in col_map.items()}

    entry_csv = rev.get("EntryFillTime")
    exit_csv = rev.get("ExitFillTime")
    if entry_csv is None or exit_csv is None:
        return 0.0

    entry_str = str(row.get(entry_csv, ""))
    exit_str = str(row.get(exit_csv, ""))
    if not entry_str or not exit_str or entry_str in ("nan", "") or exit_str in ("nan", ""):
        return 0.0

    try:
        parts_e = entry_str.split(":")
        parts_x = exit_str.split(":")
        secs_e = int(parts_e[0]) * 3600 + int(parts_e[1]) * 60 + int(float(parts_e[2]))
        secs_x = int(parts_x[0]) * 3600 + int(parts_x[1]) * 60 + int(float(parts_x[2]))
        if secs_x < secs_e:
            secs_x += 86400
        return (secs_x - secs_e) / 60.0
    except (ValueError, IndexError):
        return 0.0
