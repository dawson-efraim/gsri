"""Streamlit dashboard for GSRI platform."""
import streamlit as st
import sys
sys.path.insert(0, "C:/Users/dawso/Downloads/hermes projects/gsri")
from src.config import DATA_SOURCES, ALERT_THRESHOLDS, WEIGHTING_METHODS, RISK_CATEGORIES
from src.database import Database
from src.data_ingestion import DataIngestion
from src.risk_calculator import RiskCalculator
from src.alerts import RiskAlertSystem
from src.forecasting import RiskForecaster
from src.visualizations import (
    gsri_gauge, category_bar, risk_map, trend_chart,
    scenario_comparison, momentum_chart, freshness_indicator
)
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="GSRI - Global Systemic Risk Intelligence",
                   layout="wide", page_icon="🌍")


def run_pipeline():
    """Run the full data pipeline and return results."""
    ingest = DataIngestion()
    ingest.run_all()
    ingest.close()

    rc = RiskCalculator()
    results = rc.compute_gsri_all_methods()
    momentum = rc.compute_momentum()
    freshness = rc.get_indicator_freshness()
    compound = rc.detect_compound_risk(results["category_scores"])
    rc.close()

    alert_sys = RiskAlertSystem()
    alerts = alert_sys.evaluate(results["expert"], results["category_scores"], momentum)
    active_alerts = alert_sys.get_active()
    alert_sys.close()

    return results, momentum, freshness, compound, alerts, active_alerts


def main():
    st.title("🌍 Global Systemic Risk Intelligence (GSRI)")
    st.markdown("---")

    # Sidebar
    st.sidebar.header("Controls")
    run = st.sidebar.button("🔄 Run Data Pipeline", key="run_pipeline")
    refresh = st.sidebar.slider("Dashboard auto-refresh (s)", 10, 600, 300)

    if run:
        with st.spinner("Running data pipeline..."):
            results, momentum, freshness, compound, alerts, active_alerts = run_pipeline()
        st.success("Pipeline complete!")

    # Initialize session state
    if "gsri_data" not in st.session_state:
        st.session_state.gsri_data = None

    if st.session_state.gsri_data is None and not run:
        with st.spinner("Loading data..."):
            try:
                results, momentum, freshness, compound, alerts, active_alerts = run_pipeline()
                st.session_state.gsri_data = results
            except Exception as e:
                st.error(f"Error loading data: {e}")
                st.session_state.gsri_data = None
    else:
        results = st.session_state.gsri_data

    if results is None:
        st.warning("No data available. Click 'Run Data Pipeline' to start.")
        return

    gsri = results["expert"]

    # ── Header ──────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("GSRI Score", f"{gsri}/100", f"{momentum['30d']:+} (30d)")
    col2.metric("Risk Level",
                "HIGH" if gsri >= 60 else "ELEVATED" if gsri >= 40 else "MODERATE")
    col3.metric("Momentum", momentum["label"])
    col4.metric("Last Update", results["timestamp"][:10])

    st.markdown("---")

    # ── Main dashboard ──────────────────────────────────
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.subheader("GSRI Gauge")
        st.plotly_chart(gsri_gauge(gsri), use_container_width=True)

        st.subheader("GSRI Trend")
        st.plotly_chart(trend_chart([gsri] * 10), use_container_width=True)

    with right_col:
        st.subheader("Risk by Category")
        st.plotly_chart(category_bar(results["category_scores"]),
                        use_container_width=True)

        st.subheader("Momentum")
        st.plotly_chart(momentum_chart([gsri] * 5), use_container_width=True)

    # ── Data Freshness ──────────────────────────────────
    st.subheader("Data Pipeline Status")
    freshness_df = pd.DataFrame(freshness)
    st.dataframe(freshness_df, use_container_width=True)

    # ── Alerts ──────────────────────────────────────────
    if alerts:
        st.subheader("⚠ Active Alerts")
        for a in alerts:
            color = "red" if a["severity"] == "CRITICAL" else "orange" if a["severity"] == "HIGH" else "yellow"
            st.markdown(f"**[{a['severity']}]** {a['description']} "
                        f"(confidence: {a['confidence']:.0%})",
                        unsafe_allow_html=True)

    # ── Scenario Simulator ──────────────────────────────
    st.markdown("---")
    st.subheader("🔬 Scenario Simulator")
    col1, col2 = st.columns(2)
    with col1:
        climate_adj = st.slider("Climate Change", -50, 100, 0, key="scenario_climate")
        water_adj = st.slider("Water Stress", -50, 100, 0, key="scenario_water")
        food_adj = st.slider("Food Security", -50, 100, 0, key="scenario_food")
    with col2:
        energy_adj = st.slider("Energy Crisis", -50, 100, 0, key="scenario_energy")
        geo_adj = st.slider("Geopolitical Risk", -50, 100, 0, key="scenario_geo")
        eco_adj = st.slider("Economic Instability", -50, 100, 0, key="scenario_eco")

    if st.button("Calculate Scenario"):
        adj = (climate_adj * 0.25 + water_adj * 0.15 + food_adj * 0.15 +
               energy_adj * 0.10 + geo_adj * 0.05 + eco_adj * 0.10)
        projected = min(100, max(0, gsri + adj))
        st.plotly_chart(scenario_comparison(gsri, projected), use_container_width=True)
        st.write(f"**Projected GSRI: {projected:.1f}** (change: {adj:+.1f})")

    # ── Footer disclaimer ───────────────────────────────
    st.markdown("---")
    st.markdown("""
    > ⚠️ **Scientific Disclaimer**
    > This system does not predict the end of the world or the exact date of human extinction.
    > It is an experimental data-science model for monitoring global systemic risks and exploring
    > potential future scenarios. Predictions contain uncertainty, depend on data quality,
    > and should not be interpreted as definitive forecasts.
    """)


if __name__ == "__main__":
    main()
