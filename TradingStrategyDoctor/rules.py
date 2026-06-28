"""
Trading Strategy Doctor — Rule Engine
======================================
Deterministic rule-based analysis of trading metrics.

No AI / LLM — every rule, score, and recommendation is hard-coded logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Rule definition
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    """
    A single deterministic rule.

    *condition* receives the full metrics dict and returns True when the
    rule should fire.  *score_impact* is the number of points to add or
    subtract from the base health score.  *category* determines which
    diagnosis section the message appears in.
    """
    name: str
    category: str           # "strengths" | "weaknesses" | "risks" | "recommendations"
    condition: Callable[[dict], bool]
    message: str
    severity: str           # "good" | "warning" | "critical" | "info"
    score_impact: int = 0   # Positive = reward, negative = penalty


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------
# The rules are stored in a list and evaluated in order.

def _rules() -> list[Rule]:
    return [
        # --- Profit Factor ---
        Rule(
            name="pf_excellent",
            category="strengths",
            condition=lambda m: isinstance(m.get("profitFactor"), (int, float)) and m["profitFactor"] > 2.0,
            message="Excellent Profit Factor (> 2.0)",
            severity="good",
            score_impact=15,
        ),
        Rule(
            name="pf_good",
            category="strengths",
            condition=lambda m: isinstance(m.get("profitFactor"), (int, float)) and 1.5 < m["profitFactor"] <= 2.0,
            message="Good Profit Factor (> 1.5)",
            severity="good",
            score_impact=10,
        ),
        Rule(
            name="pf_warning",
            category="weaknesses",
            condition=lambda m: isinstance(m.get("profitFactor"), (int, float)) and m["profitFactor"] < 1.2,
            message="Profit Factor below 1.2 — strategy may not be profitable after costs",
            severity="warning",
            score_impact=-10,
        ),

        # --- Win Rate ---
        Rule(
            name="wr_excellent",
            category="strengths",
            condition=lambda m: m.get("winRate", 0) > 65,
            message="Excellent Win Rate (> 65%)",
            severity="good",
            score_impact=15,
        ),
        Rule(
            name="wr_good",
            category="strengths",
            condition=lambda m: 55 < m.get("winRate", 0) <= 65,
            message="Good Win Rate (> 55%)",
            severity="good",
            score_impact=10,
        ),
        Rule(
            name="wr_warning",
            category="weaknesses",
            condition=lambda m: m.get("winRate", 100) < 45,
            message="Win Rate below 45% — consider reviewing entry criteria",
            severity="warning",
            score_impact=-10,
        ),

        # --- Risk-Reward ---
        Rule(
            name="rr_warning",
            category="weaknesses",
            condition=lambda m: m.get("avgRR", 999) < 1.5,
            message="Average Risk-Reward below 1.5 — winners not large enough relative to losers",
            severity="warning",
            score_impact=-10,
        ),
        Rule(
            name="avg_winner_lt_loser",
            category="risks",
            condition=lambda m: (m.get("avgWinner", 0) > 0 and m.get("avgLoser", 0) > 0
                                 and m["avgWinner"] < m["avgLoser"]),
            message="Average Winner is smaller than Average Loser — the strategy loses more per losing trade than it gains on winners",
            severity="critical",
            score_impact=-25,
        ),

        # --- Drawdown ---
        Rule(
            name="dd_critical",
            category="risks",
            condition=lambda m: m.get("maxDrawdown", 0) > 20,
            message="Maximum Drawdown exceeds 20% threshold",
            severity="critical",
            score_impact=-20,
        ),

        # --- Over-trading ---
        Rule(
            name="overtrading",
            category="risks",
            condition=lambda m: m.get("avgTradeDuration", 999) < 2,
            message="Average trade duration under 2 minutes — possible over-trading or noise trading",
            severity="warning",
            score_impact=-5,
        ),

        # --- Sample size ---
        Rule(
            name="small_sample",
            category="recommendations",
            condition=lambda m: m.get("totalTrades", 999) < 30,
            message="Fewer than 30 trades — conclusions may not be statistically significant. Collect more data.",
            severity="info",
            score_impact=0,
        ),

        # --- Recommendations based on combined signals ---
        Rule(
            name="rec_rr",
            category="recommendations",
            condition=lambda m: m.get("avgRR", 999) < 1.5,
            message="Increase Risk-Reward ratio above 1.8 by widening profit targets or tightening stops",
            severity="info",
            score_impact=0,
        ),
        Rule(
            name="rec_loser_size",
            category="recommendations",
            condition=lambda m: (m.get("avgLoser", 0) > 0 and m.get("avgWinner", 0) > 0
                                 and m["avgWinner"] < m["avgLoser"]),
            message="Reduce losing trade size — consider scaling into winners and cutting losers faster",
            severity="info",
            score_impact=0,
        ),
        Rule(
            name="rec_volatility",
            category="recommendations",
            condition=lambda m: m.get("maxDrawdown", 0) > 15,
            message="Add a volatility filter (e.g. ATR threshold) to avoid high-volatility regimes",
            severity="info",
            score_impact=0,
        ),
        Rule(
            name="rec_htf",
            category="recommendations",
            condition=lambda m: m.get("winRate", 100) < 50,
            message="Filter trades using higher timeframe trend to improve win rate",
            severity="info",
            score_impact=0,
        ),
    ]


# ---------------------------------------------------------------------------
# Health score
# ---------------------------------------------------------------------------

def compute_health_score(metrics: dict[str, Any]) -> dict[str, Any]:
    """
    Compute a strategy health score out of 100.

    Returns:
        {"score": int, "color": str, "label": str}
    """
    if metrics.get("totalTrades", 0) == 0:
        return {"score": 0, "color": "#dc3545", "label": "No Data"}

    base_score = 50  # start at neutral
    for rule in _rules():
        try:
            if rule.condition(metrics):
                base_score += rule.score_impact
        except Exception:
            continue  # defensive — malformed data shouldn't crash scoring

    score = max(0, min(100, base_score))

    if score >= 70:
        color = "#198754"   # green
        label = "Good"
    elif score >= 40:
        color = "#ffc107"   # yellow
        label = "Fair"
    else:
        color = "#dc3545"   # red
        label = "Poor"

    return {"score": score, "color": color, "label": label}


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------

def generate_diagnosis(metrics: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    """
    Evaluate all rules and group results into diagnosis sections.

    Returns:
        {
            "strengths":        [{"message": str, "severity": str}, ...],
            "weaknesses":       [...],
            "risks":            [...],
            "recommendations":  [...],
        }
    """
    sections: dict[str, list[dict[str, str]]] = {
        "strengths": [],
        "weaknesses": [],
        "risks": [],
        "recommendations": [],
    }

    for rule in _rules():
        try:
            if rule.condition(metrics):
                sections[rule.category].append({
                    "message": rule.message,
                    "severity": rule.severity,
                })
        except Exception:
            continue

    return sections
