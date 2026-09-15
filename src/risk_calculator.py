"""Risk calculation engine: normalize indicators, compute category risk, GSRI."""
import sqlite3
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from src.config import (
    NORMALIZATION_BOUNDS, INDICATOR_DIRECTION, INDICATOR_CATEGORIES,
    RISK_CATEGORIES, EXPERT_CATEGORY_WEIGHTS, WEIGHTING_METHODS
)
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


class RiskCalculator:
    def __init__(self, db_path: str = "data/gsri.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

    # ── helpers ────────────────────────────────────────────────
    def _get_all_indicators(self) -> List[dict]:
        cur = self.conn.execute('''
            SELECT i.id, i.name, i.category, i.bounds_min, i.bounds_max, i.direction, s.name as source_name
            FROM indicators i JOIN data_sources s ON i.source_id = s.id
        ''')
        return [
            {"id": r[0], "name": r[1], "category": r[2],
             "bounds_min": r[3], "bounds_max": r[4],
             "direction": r[5], "source_name": r[6]}
            for r in cur.fetchall()
        ]

    def _get_latest_value(self, indicator_id: int) -> Optional[float]:
        cur = self.conn.execute('''
            SELECT value FROM data_points
            WHERE indicator_id = ? AND is_valid = 1
            ORDER BY timestamp DESC LIMIT 1
        ''', (indicator_id,))
        row = cur.fetchone()
        return row[0] if row else None

    def _get_time_series(self, indicator_id: int, limit: int = 365) -> pd.Series:
        cur = self.conn.execute('''
            SELECT timestamp, value FROM data_points
            WHERE indicator_id = ? AND is_valid = 1
            ORDER BY timestamp DESC LIMIT ?
        ''', (indicator_id, limit))
        rows = cur.fetchall()
        if not rows:
            return pd.Series(dtype=float)
        df = pd.DataFrame(rows, columns=['timestamp', 'value'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna().set_index('timestamp').sort_index()
        return df['value']

    # ── normalization ──────────────────────────────────────────
    def normalize_indicator(self, name: str, value: float) -> float:
        """Normalize to 0-100. Higher = more risk."""
        bounds = NORMALIZATION_BOUNDS.get(name, (0, 100))
        b_min, b_max = bounds
        if b_max == b_min:
            return 50.0

        direction = INDICATOR_DIRECTION.get(name, 1)
        raw = (value - b_min) / (b_max - b_min) * 100
        raw = max(0.0, min(100.0, raw))

        if direction == -1:
            raw = 100.0 - raw

        return round(raw, 2)

    # ── category risk ──────────────────────────────────────────
    def compute_category_scores(self) -> Dict[str, float]:
        """Average normalized indicator score per category."""
        indicators = self._get_all_indicators()
        cat_scores: Dict[str, List[float]] = {c: [] for c in RISK_CATEGORIES}

        for ind in indicators:
            val = self._get_latest_value(ind["id"])
            if val is None:
                continue
            norm = self.normalize_indicator(ind["name"], val)
            cat = ind.get("category", "society")
            if cat in cat_scores:
                cat_scores[cat].append(norm)

        result = {}
        for cat, scores in cat_scores.items():
            result[cat] = round(np.mean(scores), 2) if scores else 50.0
        return result

    # ── GSRI weighting methods ─────────────────────────────────
    def compute_gsri_weighted(self, category_scores: Dict[str, float],
                               weights: Dict[str, float]) -> float:
        total = 0.0
        w_sum = 0.0
        for cat, w in weights.items():
            if cat in category_scores:
                total += category_scores[cat] * w
                w_sum += w
        return round(total / w_sum, 2) if w_sum > 0 else 50.0

    def gsri_expert(self, cat_scores: Dict[str, float]) -> float:
        return self.compute_gsri_weighted(cat_scores, EXPERT_CATEGORY_WEIGHTS)

    def gsri_equal(self, cat_scores: Dict[str, float]) -> float:
        w = {c: 1.0 / len(RISK_CATEGORIES) for c in RISK_CATEGORIES}
        return self.compute_gsri_weighted(cat_scores, w)

    def gsri_statistical(self, cat_scores: Dict[str, float]) -> float:
        """Weight by inverse variance across available categories."""
        indicators = self._get_all_indicators()
        cat_values: Dict[str, List[float]] = {c: [] for c in RISK_CATEGORIES}
        for ind in indicators:
            series = self._get_time_series(ind["id"], limit=60)
            if len(series) < 3:
                continue
            normed = series.apply(lambda v: self.normalize_indicator(ind["name"], v))
            cat = ind.get("category", "society")
            if cat in cat_values:
                cat_values[cat].extend(normed.tolist())

        inv_var = {}
        for cat, vals in cat_values.items():
            if len(vals) >= 3:
                var = np.var(vals)
                inv_var[cat] = 1.0 / (var + 1e-6)
            else:
                inv_var[cat] = 1.0

        total_w = sum(inv_var.get(c, 0) for c in RISK_CATEGORIES)
        weights = {c: inv_var.get(c, 0) / total_w for c in RISK_CATEGORIES} if total_w > 0 else {c: 1/len(RISK_CATEGORIES) for c in RISK_CATEGORIES}
        return self.compute_gsri_weighted(cat_scores, weights)

    def gsri_pca(self, cat_scores: Dict[str, float]) -> float:
        """PCA-based: use first component loadings as weights."""
        indicators = self._get_all_indicators()
        matrix_rows = []
        for ind in indicators:
            series = self._get_time_series(ind["id"], limit=60)
            if len(series) < 3:
                continue
            normed = series.apply(lambda v: self.normalize_indicator(ind["name"], v))
            cat = ind.get("category", "society")
            matrix_rows.append({"category": cat, "values": normed.tolist()})

        if not matrix_rows:
            return self.gsri_equal(cat_scores)

        # Build matrix: columns = time, rows = indicators.
        # Rows have different history lengths; align on the shortest overlap window
        # so every row has equal length (np.array needs a rectangular matrix).
        min_len = min(len(r["values"]) for r in matrix_rows)
        if min_len < 3:
            return self.gsri_equal(cat_scores)
        mat = np.array([r["values"][-min_len:] for r in matrix_rows])
        if mat.shape[0] < 3 or mat.shape[1] < 3:
            return self.gsri_equal(cat_scores)

        scaler = StandardScaler()
        mat_scaled = scaler.fit_transform(mat)

        pca = PCA(n_components=1)
        pca.fit(mat_scaled.T)
        loadings = np.abs(pca.components_[0])

        # Average loadings per category
        cat_weights = {}
        idx = 0
        for r in matrix_rows:
            cat = r["category"]
            cat_weights[cat] = cat_weights.get(cat, []) + [loadings[idx]]
            idx += 1

        avg_w = {c: np.mean(vals) for c, vals in cat_weights.items()}
        total_w = sum(avg_w.values())
        weights = {c: avg_w.get(c, 0) / total_w for c in RISK_CATEGORIES} if total_w > 0 else {c: 1/len(RISK_CATEGORIES) for c in RISK_CATEGORIES}
        return self.compute_gsri_weighted(cat_scores, weights)

    # ── full GSRI calculation ──────────────────────────────────
    def compute_gsri_all_methods(self) -> Dict:
        cat_scores = self.compute_category_scores()

        results = {
            "category_scores": cat_scores,
            "expert": self.gsri_expert(cat_scores),
            "equal": self.gsri_equal(cat_scores),
            "statistical": self.gsri_statistical(cat_scores),
            "pca": self.gsri_pca(cat_scores),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Store calculation
        self.conn.execute('''
            INSERT INTO risk_calculations (calculation_timestamp, data_version, model_version, gsri_score, weights_json, method)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            results["timestamp"],
            "v1",
            "v1",
            results["expert"],
            json.dumps(EXPERT_CATEGORY_WEIGHTS),
            "expert"
        ))
        self.conn.commit()

        return results

    # ── momentum ───────────────────────────────────────────────
    def compute_momentum(self) -> Dict:
        """Compute GSRI change over 7, 30, 90 days."""
        cur = self.conn.execute('''
            SELECT calculation_timestamp, gsri_score FROM risk_calculations
            ORDER BY calculation_timestamp DESC LIMIT 100
        ''')
        rows = cur.fetchall()
        if not rows:
            return {"current": 50.0, "7d": 0, "30d": 0, "90d": 0, "label": "Stable"}

        current = rows[0][1]
        now = datetime.fromisoformat(rows[0][0])

        changes = {}
        for label, days in [("7d", 7), ("30d", 30), ("90d", 90)]:
            target = now - pd.Timedelta(days=days)
            closest = None
            for ts, score in reversed(rows):
                dt = datetime.fromisoformat(ts)
                if dt <= target:
                    closest = score
                    break
            changes[label] = round(current - closest, 2) if closest is not None else 0.0

        # Momentum label
        change_30 = changes["30d"]
        if change_30 <= -5:
            label = "Rapidly Improving"
        elif change_30 <= -2:
            label = "Improving"
        elif change_30 <= 2:
            label = "Stable"
        elif change_30 <= 5:
            label = "Deteriorating"
        else:
            label = "Rapidly Deteriorating"

        return {
            "current": current,
            "7d": changes["7d"],
            "30d": changes["30d"],
            "90d": changes["90d"],
            "label": label
        }

    # ── compound risk detection ────────────────────────────────
    def detect_compound_risk(self, cat_scores: Dict[str, float], threshold: float = 55.0) -> List[Dict]:
        """Detect when multiple categories are simultaneously high/increasing."""
        alerts = []
        deteriorating = [c for c, s in cat_scores.items() if s >= threshold]

        if len(deteriorating) >= 3:
            alerts.append({
                "type": "compound_risk",
                "severity": "HIGH" if len(deteriorating) >= 5 else "MEDIUM",
                "categories": deteriorating,
                "description": f"Multiple risk categories elevated: {', '.join(deteriorating)}",
                "potential_cascade": self._suggest_cascade(deteriorating)
            })

        return alerts

    def _suggest_cascade(self, cats: List[str]) -> str:
        cascade_map = {
            frozenset(["climate", "water", "food"]): "Climate → Water → Food cascade",
            frozenset(["climate", "water", "food", "economy"]): "Climate → Water → Food → Economy cascade",
            frozenset(["water", "food", "society"]): "Water → Food → Society cascade",
            frozenset(["energy", "economy"]): "Energy → Economy cascade",
            frozenset(["geopolitics", "economy", "society"]): "Geopolitics → Economy → Society cascade"
        }
        cat_set = frozenset(cats)
        for combo, text in cascade_map.items():
            if combo.issubset(cat_set):
                return text
        return "Potential compound risk — no specific cascade pattern identified"

    # ── indicator data freshness ───────────────────────────────
    def get_indicator_freshness(self) -> List[Dict]:
        """Return data freshness metadata for all indicators."""
        indicators = self._get_all_indicators()
        result = []
        for ind in indicators:
            cur = self.conn.execute('''
                SELECT timestamp, source_timestamp FROM data_points
                WHERE indicator_id = ? AND is_valid = 1
                ORDER BY timestamp DESC LIMIT 1
            ''', (ind["id"],))
            row = cur.fetchone()
            if row:
                try:
                    ts = datetime.fromisoformat(row[0])
                    age_days = (datetime.utcnow() - ts).days
                except Exception:
                    age_days = 999
                result.append({
                    "name": ind["name"],
                    "category": ind["category"],
                    "source": ind["source_name"],
                    "last_timestamp": row[0],
                    "age_days": age_days
                })
            else:
                result.append({
                    "name": ind["name"],
                    "category": ind["category"],
                    "source": ind["source_name"],
                    "last_timestamp": None,
                    "age_days": 999
                })
        return result

    def close(self):
        if self.conn:
            self.conn.close()
