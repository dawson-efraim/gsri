# Global Systemic Risk Intelligence (GSRI) Platform

## Overview
A lightweight Python system that continuously ingests public data, validates it, calculates a **Global Systemic Risk Index (GSRI)**, and surfaces real‑time insights through an interactive Streamlit dashboard.

- **Data sources**: NOAA CO₂, World Bank, FAO, USGS, commodity price APIs, etc.
- **Risk calculation**: Normalized indicators → category scores → GSRI (expert, equal, statistical, PCA weightings).
- **Features**: Momentum tracking, compound‑risk detection, early‑warning alerts, scenario simulation, world‑risk map.
- **Stack**: Python 3.14, SQLite, Pandas, NumPy, scikit‑learn, Plotly, Streamlit.
- **Automation**: CLI sub‑commands (`ingest`, `risk`, `alerts`, `forecast`, `all`).

## Repository Layout
```
GSRI/
├─ data/                # SQLite DB (gsri.db) & cache folder
├─ notebooks/           # Exploratory analysis (optional)
├─ src/                 # Core modules
│   ├─ __init__.py
│   ├─ __main__.py      # CLI entry point
│   ├─ config.py        # Sources, indicators, bounds, weights
│   ├─ database.py      # SQLite schema & helpers
│   ├─ data_ingestion.py# API fetch + validation
│   ├─ risk_calculator.py# Normalisation, GSRI, momentum, compound risk
│   ├─ alerts.py        # Early warning system
│   ├─ forecasting.py   # ARIMA / RF future GSRI forecasts
│   └─ visualizations.py# Plotly chart helpers
├─ dashboard.py         # Streamlit UI
├─ requirements.txt     # Python dependencies
└─ README.md            # This file
```

## Quick Start
```bash
# Clone (keep private until ready)
git clone <repo‑url>
cd GSRI

# Install deps (virtualenv recommended)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the full pipeline (fetch, calc, alerts)
python -m src all

# Launch the dashboard (auto‑refresh every 5 min)
streamlit run dashboard.py
```

## Core Commands
| Command | What it does |
|---------|--------------|
| `python -m src ingest` | Pull latest data from all sources, store in SQLite. |
| `python -m src risk`   | Compute GSRI (all weighting methods) + momentum, print to console. |
| `python -m src alerts` | Evaluate thresholds, list active alerts. |
| `python -m src forecast`| Produce short‑term GSRI forecast (ARIMA default). |
| `python -m src all`    | Run **ingest → risk → alerts** in one step. |

## Data Pipeline Details
1. **Metadata init** – `src/config.py` declares every source, indicator, update frequency, units, and normalisation bounds.
2. **Ingestion** – `src/data_ingestion.py` fetches CSV/JSON, validates against bounds (±20 % margin), flags impossible values, and writes clean rows to `data/gsri.db`.
3. **Validation** – Rejects NaN, non‑numeric, out‑of‑range after margin; keeps last valid observation.
4. **Storage** – SQLite tables for `data_sources`, `indicators`, `data_points`, `risk_calculations`, `alerts` (see `src/database.py`).

## Risk Calculation Workflow (`src/risk_calculator.py`)
1. **Normalize** each indicator to a 0‑100 scale (higher = more risk, direction handled).
2. **Category scores** – average of normalized indicators per category.
3. **GSRI methods**:
   - **Expert** – pre‑defined expert weights (`EXPERT_CATEGORY_WEIGHTS`).
   - **Equal** – uniform weight across categories.
   - **Statistical** – inverse‑variance weighting across historical data.
   - **PCA** – first principal component loadings as weights (aligned on shortest time series).
4. **Momentum** – 7 / 30 / 90 day GSRI change, label (`Stable`, `Improving`, `Deteriorating`, etc.).
5. **Compound risk** – detects ≥ 3 categories above the `ALERT_THRESHOLDS['category_spike']` and suggests cascade patterns.
6. **Persist** – writes calculation row (timestamp, GSRI, method, weights) to DB.

## Alerts (`src/alerts.py`)
- **GSRI level** – Critical ≥ 75, High ≥ 60.
- **Category spikes** – any category ≥ `gsri_high` (60) triggers severity based on score.
- **Momentum** – rapid rise ≥ 5 pts over 30 days → HIGH.
- **Compound risk** – ≥ 3 elevated categories → HIGH/Medium.
- Alerts stored in `alerts` table; `get_active(hours=72)` returns recent alerts.

## Forecasting (`src/forecasting.py`)
- **ARIMA** – fits a simple `(5,1,0)` model on historical GSRI series (daily).
- **Random Forest** – alternative trend model using day‑of‑year & year features.
- Returns 7‑day forecast (extendable to 30 / 90 days). Future work: ensemble, probabilistic intervals.

## Dashboard Highlights (`dashboard.py`)
- **GSRI gauge** – colour‑coded (green < 40, yellow 40‑60, orange > 60).
- **Category bar chart** – heat‑map style showing risk per domain.
- **Trend chart** – recent GSRI line (placeholder data; replaced by DB in production).
- **Momentum chart** – area visual of GSRI changes.
- **Data freshness table** – last update per indicator, colour‑coded freshness.
- **Active alerts** – list with severity colours.
- **Scenario simulator** – sliders adjust % change per domain, recompute projected GSRI on‑fly.
- **Scientific disclaimer** – visible footer.

## Auditable Calculations
Every GSRI run stores:
```json
{
  "calculation_timestamp": "2026-09-15T22:10:12Z",
  "data_version": "v1",
  "model_version": "v1",
  "gsri_score": 47.02,
  "weights_json": "{…}",
  "method": "expert"
}
```
All raw indicator values, timestamps, and validation flags are kept in `data_points`, enabling full reproducibility.

## Future Roadmap (v1 → v2)
- Add biodiversity, climate‑extreme, and socio‑political indicators.
- Implement hourly scheduler (GitHub Actions / cron) for real‑time updates.
- Dockerize with Postgres for scaling.
- CI/CD pipeline with automated tests for ingestion & calculation.
- Enhanced forecasting (LSTM, Prophet, uncertainty bands).
- User authentication & per‑user alert subscriptions.

## License & Contributions
- MIT License – feel free to fork, improve, submit PRs.
- Keep the repo private until a stable version is ready for public showcase.

---
*Built for learning, portfolio‑ready, and ready to evolve into a production‑grade monitoring platform.*