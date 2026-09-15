"""Visualization helpers for GSRI dashboard."""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import Dict, List


def gsri_gauge(score: float) -> go.Figure:
    """Create a gauge chart for GSRI score."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": "Global Systemic Risk Index"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "darkred" if score >= 60 else "orange" if score >= 40 else "green"},
            "steps": [
                {"range": [0, 40], "color": "lightgreen"},
                {"range": [40, 60], "color": "yellow"},
                {"range": [60, 100], "color": "orange"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": score
            }
        }
    ))
    fig.update_layout(height=350)
    return fig


def category_bar(scores: Dict[str, float]) -> go.Figure:
    """Bar chart of category risk scores."""
    cats = list(scores.keys())
    vals = list(scores.values())
    colors = ["red" if v >= 60 else "orange" if v >= 40 else "green" for v in vals]
    fig = go.Figure(data=[go.Bar(x=cats, y=vals, marker_color=colors)])
    fig.update_layout(
        title="Risk by Category",
        xaxis_title="Category",
        yaxis_title="Score (0-100)",
        height=400,
        template="plotly_dark"
    )
    return fig


def risk_map(country_risk: Dict[str, float]) -> go.Figure:
    """Choropleth world map."""
    fig = px.choropleth(
        locations=list(country_risk.keys()),
        locationmode="country names",
        color=list(country_risk.values()),
        color_continuous_scale="RdYlGn_r",
        title="Global Risk by Country",
        labels={"color": "Risk Score"}
    )
    fig.update_layout(height=500, template="plotly_dark")
    return fig


def trend_chart(history: List[float], dates: List[str] = None) -> go.Figure:
    """GSRI trend over time."""
    if dates is None:
        dates = list(range(len(history)))
    fig = go.Figure(data=[go.Scatter(x=dates, y=history, mode="lines+markers")])
    fig.update_layout(
        title="GSRI Trend",
        xaxis_title="Date",
        yaxis_title="GSRI Score",
        height=400,
        template="plotly_dark"
    )
    return fig


def scenario_comparison(current: float, projected: float) -> go.Figure:
    """Compare current vs scenario GSRI."""
    fig = go.Figure(data=[
        go.Bar(name="Current", x=["GSRI"], y=[current], marker_color="blue"),
        go.Bar(name="Scenario", x=["GSRI"], y=[projected], marker_color="red")
    ])
    fig.update_layout(
        title="Scenario Comparison",
        yaxis_title="GSRI Score",
        height=350,
        template="plotly_dark"
    )
    return fig


def freshness_indicator(age_days: int) -> str:
    if age_days <= 1:
        return "🟢 Current"
    elif age_days <= 7:
        return "🟡 Recent"
    elif age_days <= 30:
        return "🟠 Aging"
    else:
        return "🔴 Stale"


def momentum_chart(history: List[float]) -> go.Figure:
    """Show momentum as area chart."""
    x = list(range(len(history)))
    fig = go.Figure(data=[go.Scatter(x=x, y=history, fill="tozeroy",
                        mode="lines", name="GSRI")])
    fig.update_layout(
        title="GSRI Momentum",
        xaxis_title="Periods",
        yaxis_title="GSRI",
        height=350,
        template="plotly_dark"
    )
    return fig
