"""GSRI CLI entry point. Usage: python -m src [ingest|risk|alerts|forecast|all]"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_ingestion import DataIngestion
from src.risk_calculator import RiskCalculator
from src.alerts import RiskAlertSystem
from src.forecasting import RiskForecaster


def cmd_ingest(_args):
    ing = DataIngestion()
    ing.run_all()
    ing.close()


def cmd_risk(_args):
    rc = RiskCalculator()
    out = rc.compute_gsri_all_methods()
    print("Category scores:", out["category_scores"])
    print("GSRI expert:", out["expert"])
    print("GSRI equal:", out["equal"])
    print("GSRI statistical:", out["statistical"])
    print("GSRI pca:", out["pca"])
    print("Momentum:", rc.compute_momentum())
    rc.close()


def cmd_alerts(_args):
    rc = RiskCalculator()
    out = rc.compute_gsri_all_methods()
    momentum = rc.compute_momentum()
    rc.close()
    al = RiskAlertSystem()
    found = al.evaluate(out["expert"], out["category_scores"], momentum)
    print(f"{len(found)} alert(s):")
    for a in found:
        print(f"  [{a['severity']}] {a['category']}: {a['description']}")
    al.close()


def cmd_forecast(_args):
    fc = RiskForecaster()
    print(fc.forecast_gsri())
    fc.close()


def cmd_all(_args):
    cmd_ingest(_args)
    cmd_risk(_args)
    cmd_alerts(_args)


def main():
    p = argparse.ArgumentParser(description="GSRI pipeline CLI")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest")
    sub.add_parser("risk")
    sub.add_parser("alerts")
    sub.add_parser("forecast")
    sub.add_parser("all")
    args = p.parse_args()
    {"ingest": cmd_ingest, "risk": cmd_risk, "alerts": cmd_alerts,
     "forecast": cmd_forecast, "all": cmd_all}[args.cmd](args)


if __name__ == "__main__":
    main()
