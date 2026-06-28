"""
Trading Strategy Doctor — FastAPI Application
==============================================
A quantitative research dashboard for reviewing algorithmic trading strategies.

Usage:
    pip install -r requirements.txt
    uvicorn app:app --reload
"""

from __future__ import annotations

import io
import os
import json
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Optional
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, Query, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from analysis import (
    detect_schema,
    validate_columns,
    parse_trades,
    apply_filters,
    get_filter_options,
    Filters,
)
from metrics import (
    compute_metrics,
    compute_equity_curve,
    compute_monthly_pnl,
    compute_pnl_distribution,
    compute_drawdown_series,
    compute_duration_histogram,
    compute_win_loss_summary,
)
from rules import compute_health_score, generate_diagnosis


# Max upload size: 800 MB
MAX_UPLOAD_MB = 800
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).parent
SAMPLE_CSV = HERE / "sample_data" / "sample_trades.csv"
TEMPLATES = HERE / "templates"
STATIC = HERE / "static"


# ---------------------------------------------------------------------------
# Application lifespan — load sample data at startup
# ---------------------------------------------------------------------------

# In-memory store for the current trade DataFrame (no database).
_df_store: dict[str, pd.DataFrame] = {}


def _load_sample() -> pd.DataFrame:
    """Load and parse the sample CSV."""
    if not SAMPLE_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(SAMPLE_CSV)
    errors = validate_columns(df)
    if errors:
        raise RuntimeError(f"Sample CSV validation failed: {errors}")
    col_map = detect_schema(df)
    df = parse_trades(df)
    return df


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — load sample data
    _df_store["trades"] = _load_sample()
    yield
    # Shutdown — nothing to clean up


# ---------------------------------------------------------------------------
# FastAPI initialisation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Trading Strategy Doctor",
    description="Quantitative research dashboard for reviewing algorithmic trading strategies.",
    version="1.0.0",
    lifespan=lifespan,
)

# Session middleware (signed cookie — no database)
app.add_middleware(SessionMiddleware, secret_key=os.urandom(24).hex())

# Static files & templates
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES))


# ---------------------------------------------------------------------------
# Helper — get current trades DataFrame
# ---------------------------------------------------------------------------

def _get_df(request: Request) -> pd.DataFrame:
    """
    Return the trades DataFrame.
    If a session has a custom upload flag, return the global store.
    (Storing large DataFrames in the session cookie is impractical,
    so we keep one in-memory store keyed by a session token.)
    """
    return _df_store.get("trades", pd.DataFrame())


def _parse_filters(request: Request) -> Filters:
    """Parse filter query parameters from the request."""
    return Filters(
        symbols=list(filter(None, request.query_params.getlist("symbol"))),
        strategies=list(filter(None, request.query_params.getlist("strategy"))),
        sessions=list(filter(None, request.query_params.getlist("session"))),
        timeframes=list(filter(None, request.query_params.getlist("timeframe"))),
        state_machines=list(filter(None, request.query_params.getlist("stateMachine"))),
        exit_reasons=list(filter(None, request.query_params.getlist("exitReason"))),
        date_from=_parse_date(request.query_params.get("dateFrom")),
        date_to=_parse_date(request.query_params.get("dateTo")),
    )


def _parse_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Routes — Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """Upload page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Main dashboard page."""
    df = _get_df(request)
    filter_opts = get_filter_options(df) if not df.empty else {}
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "filter_options": json.dumps(filter_opts),
        "has_data": not df.empty,
    })


# ---------------------------------------------------------------------------
# Routes — Upload / Reset
# ---------------------------------------------------------------------------

@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Accept a CSV upload, validate, parse, and store. Handles large files."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        return JSONResponse(
            {"ok": False, "errors": ["Please upload a .csv file."]},
            status_code=400,
        )

    # Stream to a temp file to avoid holding everything in memory at once
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    print(f"[UPLOAD] Receiving {file.filename} ...")
    try:
        total = 0
        while True:
            try:
                chunk = await file.read(1024 * 1024)  # 1 MB chunks
            except Exception as read_err:
                print(f"[UPLOAD] Read error: {read_err}")
                return JSONResponse(
                    {"ok": False, "errors": [f"Upload interrupted: {read_err}"]},
                    status_code=400,
                )
            if not chunk:
                break
            total += len(chunk)
            print(f"[UPLOAD] Received {total / 1024 / 1024:.1f} MB ...")
            if total > MAX_UPLOAD_BYTES:
                tmp.close()
                os.unlink(tmp.name)
                return JSONResponse(
                    {"ok": False, "errors": [
                        f"File too large ({total / 1024 / 1024:.0f} MB). "
                        f"Maximum allowed: {MAX_UPLOAD_MB} MB. "
                        f"Consider filtering your data or splitting into smaller files."
                    ]},
                    status_code=413,
                )
            tmp.write(chunk)
        tmp.flush()
        tmp.close()
        print(f"[UPLOAD] Finished receiving {total / 1024 / 1024:.1f} MB, reading with pandas ...")

        # Read with pandas from temp file
        df = pd.read_csv(tmp.name, low_memory=False)

    except pd.errors.EmptyDataError:
        print(f"[UPLOAD] Empty CSV")
        return JSONResponse({"ok": False, "errors": ["The CSV file is empty."]}, status_code=400)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"[UPLOAD] Error: {exc}")
        return JSONResponse({"ok": False, "errors": [f"Could not read CSV file: {exc}"]}, status_code=400)
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)

    validation_errors = validate_columns(df)
    if validation_errors:
        return JSONResponse({"ok": False, "errors": validation_errors}, status_code=400)

    df = parse_trades(df)
    _df_store["trades"] = df
    return JSONResponse({"ok": True})


@app.post("/api/reset")
async def reset_to_sample():
    """Reset to the built-in sample data."""
    _df_store["trades"] = _load_sample()
    return JSONResponse({"ok": True})


# ---------------------------------------------------------------------------
# Routes — API data (respects query-param filters)
# ---------------------------------------------------------------------------

@app.get("/api/data/filters")
async def api_filters(request: Request):
    """Return available filter options for the current dataset."""
    df = _get_df(request)
    return JSONResponse(get_filter_options(df) if not df.empty else {})


@app.get("/api/data/dashboard")
async def api_dashboard(request: Request):
    """
    Consolidated endpoint — returns ALL dashboard data in one shot.
    This avoids 8+ sequential round-trips on every filter change.
    """
    df = _get_df(request)
    filters = _parse_filters(request)
    filtered = apply_filters(df, filters)

    metrics = compute_metrics(filtered)
    health = compute_health_score(metrics)
    diagnosis = generate_diagnosis(metrics)

    return JSONResponse({
        "metrics": metrics,
        "healthScore": health,
        "diagnosis": diagnosis,
        "equity": compute_equity_curve(filtered),
        "monthlyPnl": compute_monthly_pnl(filtered),
        "pnlDistribution": compute_pnl_distribution(filtered),
        "drawdown": compute_drawdown_series(filtered),
        "durationHistogram": compute_duration_histogram(filtered),
        "winLoss": compute_win_loss_summary(filtered),
    })


@app.get("/api/data/metrics")
async def api_metrics(request: Request):
    """Return computed trading metrics, filtered."""
    df = _get_df(request)
    filters = _parse_filters(request)
    filtered = apply_filters(df, filters)
    return JSONResponse(compute_metrics(filtered))


@app.get("/api/data/health")
async def api_health(request: Request):
    """Return health score and diagnosis, filtered."""
    df = _get_df(request)
    filters = _parse_filters(request)
    filtered = apply_filters(df, filters)
    metrics = compute_metrics(filtered)
    score = compute_health_score(metrics)
    diagnosis = generate_diagnosis(metrics)
    return JSONResponse({"healthScore": score, "diagnosis": diagnosis})


@app.get("/api/data/trades")
async def api_trades(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=500),
    sort_by: str = Query("Date"),
    sort_dir: str = Query("desc"),
    search: str = Query(""),
):
    """Return filtered, sorted, paginated trades for the table."""
    df = _get_df(request)
    filters = _parse_filters(request)
    filtered = apply_filters(df, filters)

    # Client-side search
    if search:
        mask = filtered.astype(str).apply(
            lambda row: row.str.contains(search, case=False, na=False).any(), axis=1
        )
        filtered = filtered.loc[mask]

    total = len(filtered)

    # Sorting
    col_map = detect_schema(filtered)
    rev = {c.canonical: csv for csv, c in col_map.items()}
    sort_col_csv = rev.get(sort_by, sort_by)
    ascending = sort_dir.lower() != "desc"
    if sort_col_csv in filtered.columns:
        filtered = filtered.sort_values(sort_col_csv, ascending=ascending)

    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    page_df = filtered.iloc[start:end].copy()

    # Build friendly records
    records = []
    for _, row in page_df.iterrows():
        rec = {}
        for csv_col in page_df.columns:
            val = row[csv_col]
            if isinstance(val, pd.Timestamp):
                val = val.strftime("%Y-%m-%d")
            elif isinstance(val, float):
                val = round(val, 6)
            elif isinstance(val, (pd.Period, pd.Timedelta)):
                val = str(val)
            rec[csv_col] = val
        records.append(rec)

    return JSONResponse({
        "trades": records,
        "total": total,
        "page": page,
        "perPage": per_page,
        "columns": list(page_df.columns),
    })


@app.get("/api/data/equity")
async def api_equity(request: Request):
    df = _get_df(request)
    filters = _parse_filters(request)
    filtered = apply_filters(df, filters)
    return JSONResponse(compute_equity_curve(filtered))


@app.get("/api/data/pnl-distribution")
async def api_pnl_distribution(request: Request):
    df = _get_df(request)
    filters = _parse_filters(request)
    filtered = apply_filters(df, filters)
    return JSONResponse(compute_pnl_distribution(filtered))


@app.get("/api/data/monthly-pnl")
async def api_monthly_pnl(request: Request):
    df = _get_df(request)
    filters = _parse_filters(request)
    filtered = apply_filters(df, filters)
    return JSONResponse(compute_monthly_pnl(filtered))


@app.get("/api/data/drawdown")
async def api_drawdown(request: Request):
    df = _get_df(request)
    filters = _parse_filters(request)
    filtered = apply_filters(df, filters)
    return JSONResponse(compute_drawdown_series(filtered))


@app.get("/api/data/duration-histogram")
async def api_duration_histogram(request: Request):
    df = _get_df(request)
    filters = _parse_filters(request)
    filtered = apply_filters(df, filters)
    return JSONResponse(compute_duration_histogram(filtered))


@app.get("/api/data/win-loss")
async def api_win_loss(request: Request):
    df = _get_df(request)
    filters = _parse_filters(request)
    filtered = apply_filters(df, filters)
    return JSONResponse(compute_win_loss_summary(filtered))


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@app.get("/api/export/report")
async def export_report(request: Request):
    """Generate a self-contained HTML report for printing."""
    df = _get_df(request)
    filters = _parse_filters(request)
    filtered = apply_filters(df, filters)
    metrics = compute_metrics(filtered)
    health = compute_health_score(metrics)
    diagnosis = generate_diagnosis(metrics)
    filter_opts = get_filter_options(filtered)

    # Render via Jinja2 partial
    html = templates.TemplateResponse("report.html", {
        "request": request,
        "metrics": metrics,
        "healthScore": health,
        "diagnosis": diagnosis,
        "filter_options": filter_opts,
    }).body.decode("utf-8")

    return Response(
        content=html,
        media_type="text/html",
        headers={
            "Content-Disposition": "attachment; filename=trading-strategy-report.html"
        },
    )
