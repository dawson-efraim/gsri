import pathlib
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
sys.path.insert(0, "src")

from src.data_ingestion import DataIngestion
from src.risk_calculator import RiskCalculator
from src.alerts import RiskAlertSystem
from src.visualizations import (
    gsri_gauge,
    category_bar,
    trend_chart,
    scenario_comparison,
    momentum_chart,
    freshness_indicator
)
from datetime import datetime

def main():
    # ensure assets directory exists
    assets_dir = pathlib.Path("assets")
    assets_dir.mkdir(exist_ok=True)

    # run data pipeline
    ingest = DataIngestion()
    ingest.run_all()
    ingest.close()

    # calculate risk
    rc = RiskCalculator()
    results = rc.compute_gsri_all_methods()
    momentum = rc.compute_momentum()
    freshness = rc.get_indicator_freshness()
    rc.close()

    # ---- generate images ----
    import plotly.io as pio
    import plotly.graph_objects as go

    # 1. GSRI gauge
    gauge_img = gsri_gauge(results["expert"])
    gauge_path = assets_dir / "gsri_gauge.png"
    pio.write_image(gauge_img, gauge_path)

    # 2. category bar chart
    cat_scores = results["category_scores"]
    cat_img = category_bar(cat_scores)
    cat_path = assets_dir / "category_breakdown.png"
    pio.write_image(cat_img, cat_path)

    # 3. trend chart (use recent GSRI scores from calculations)
    # we can reuse the risk_calculator to get recent scores
    rc2 = RiskCalculator()
    recent_scores = []
    cur = rc2.conn.execute('SELECT calculation_timestamp, gsri_score FROM risk_calculations ORDER BY calculation_timestamp DESC LIMIT 10')
    for ts, score in cur:
        recent_scores.append(score)
    rc2.close()
    trend_img = trend_chart(recent_scores)
    trend_path = assets_dir / "trend_momentum.png"
    pio.write_image(trend_img, trend_path)

    # 4. scenario comparison
    projected = 58.0  # example
    scenario_img = scenario_comparison(results["expert"], projected)
    scenario_path = assets_dir / "scenario_sim.png"
    pio.write_image(scenario_img, scenario_path)

    # 5. data freshness bar chart
    fresh_df = pd.DataFrame(freshness)
    fig_fresh = go.Figure()
    fig_fresh.add_trace(go.Bar(x=fresh_df['name'], y=fresh_df['age_days'], marker_color='orange'))
    fresh_path = assets_dir / "data_freshness.png"
    pio.write_image(fig_fresh, fresh_path)

    # 6. alerts: simple bar chart of severity counts
    alert_sys = RiskAlertSystem()
    alerts = alert_sys.get_active()
    alert_sys.close()
    # Build severity count dataframe
    severity_counts = {}
    for a in alerts:
        severity_counts[a['severity']] = severity_counts.get(a['severity'], 0) + 1
    severity_df = pd.DataFrame(list(severity_counts.items()), columns=['severity', 'count'])
    alert_img = go.Figure(data=[go.Bar(x=severity_df['severity'], y=severity_df['count'])])
    alert_path = assets_dir / "alerts.png"
    pio.write_image(alert_img, alert_path)

    print("✅ Asset images generated in assets/")

if __name__ == "__main__":
    main()