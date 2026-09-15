"""Alert engine: early warning system with cooldown and severity."""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List
from src.config import ALERT_THRESHOLDS, RISK_CATEGORIES


class RiskAlertSystem:
    def __init__(self, db_path: str = "data/gsri.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

    def evaluate(self, gsri: float, category_scores: Dict[str, float],
                 momentum: Dict) -> List[Dict]:
        alerts = []
        alerts += self._check_threshold(gsri)
        alerts += self._check_category_spikes(category_scores)
        alerts += self._check_momentum(momentum)
        alerts += self._check_compound(category_scores)
        self._store(alerts)
        return alerts

    def _check_threshold(self, gsri: float) -> List[Dict]:
        if gsri >= ALERT_THRESHOLDS["gsri_critical"]:
            return [{"severity": "CRITICAL", "category": "GSRI",
                     "description": f"GSRI at critical level: {gsri}",
                     "confidence": 1.0}]
        if gsri >= ALERT_THRESHOLDS["gsri_high"]:
            return [{"severity": "HIGH", "category": "GSRI",
                     "description": f"GSRI elevated to high: {gsri}",
                     "confidence": 0.9}]
        return []

    def _check_category_spikes(self, cat_scores: Dict[str, float]) -> List[Dict]:
        alerts = []
        cur = self.conn.execute('''
            SELECT calculation_timestamp, weights_json FROM risk_calculations
            ORDER BY calculation_timestamp DESC LIMIT 1
        ''')
        row = cur.fetchone()
        if not row:
            return alerts

        for cat, score in cat_scores.items():
            if score >= ALERT_THRESHOLDS["gsri_high"]:
                alerts.append({
                    "severity": "HIGH" if score >= 75 else "MEDIUM",
                    "category": cat,
                    "description": f"{cat.title()} risk at {score:.1f}/100",
                    "confidence": 0.8
                })
        return alerts

    def _check_momentum(self, momentum: Dict) -> List[Dict]:
        if momentum.get("30d", 0) >= ALERT_THRESHOLDS["momentum_rapid"]:
            return [{"severity": "HIGH", "category": "Momentum",
                     "description": f"Rapid deterioration: +{momentum['30d']} pts in 30d",
                     "confidence": 0.85}]
        return []

    def _check_compound(self, cat_scores: Dict[str, float]) -> List[Dict]:
        th = ALERT_THRESHOLDS.get("compound_min_increase", 55)
        elevated = [c for c, s in cat_scores.items() if s >= th]
        if len(elevated) >= ALERT_THRESHOLDS["compound_min_categories"]:
            return [{
                "severity": "HIGH",
                "category": "Compound",
                "description": f"{len(elevated)} categories elevated: {', '.join(elevated)}",
                "confidence": 0.7
            }]
        return []

    def _store(self, alerts: List[Dict]):
        for a in alerts:
            self.conn.execute('''
                INSERT INTO alerts (alert_timestamp, severity, category, description, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (datetime.utcnow().isoformat(), a["severity"],
                  a["category"], a["description"], a.get("confidence", 0.5)))
        self.conn.commit()

    def get_active(self, hours: int = 72) -> List[Dict]:
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        cur = self.conn.execute('''
            SELECT alert_timestamp, severity, category, description, confidence
            FROM alerts WHERE alert_timestamp >= ?
            ORDER BY alert_timestamp DESC
        ''', (cutoff,))
        return [{"timestamp": r[0], "severity": r[1], "category": r[2],
                 "description": r[3], "confidence": r[4]}
                for r in cur.fetchall()]

    def close(self):
        if self.conn:
            self.conn.close()
