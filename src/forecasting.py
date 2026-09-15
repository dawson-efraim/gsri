import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from sklearn.ensemble import RandomForestRegressor
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

class RiskForecaster:
    def __init__(self, db_path: str = "data/gsri.db"):
        self.db_path = db_path
        # Need database connection to get historical data for forecasting
        import sqlite3
        self.conn = sqlite3.connect(db_path)

    def get_indicator_series(self, indicator_id: int) -> pd.Series:
        cur = self.conn.execute('''
            SELECT timestamp, value FROM data_points
            WHERE indicator_id = ? AND is_valid = 1
            ORDER BY timestamp ASC
        ''', (indicator_id,))
        rows = cur.fetchall()
        if len(rows) < 10:
            return pd.Series(dtype=float)
        df = pd.DataFrame(rows, columns=['timestamp', 'value'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df.set_index('timestamp')['value']

    def forecast_arima(self, series: pd.Series, steps: int = 7) -> pd.Series:
        """Simple ARIMA forecast."""
        try:
            # Need to resample to daily if not
            series = series.resample('D').mean().interpolate(method='linear')
            model = ARIMA(series, order=(5, 1, 0))
            model_fit = model.fit()
            return model_fit.forecast(steps=steps)
        except Exception:
            return pd.Series(dtype=float)

    def forecast_rf(self, series: pd.Series, steps: int = 7) -> pd.Series:
        """Simple trend-based RF forecast."""
        try:
            df = series.reset_index()
            df['day_of_year'] = df['timestamp'].dt.dayofyear
            df['year'] = df['timestamp'].dt.year
            
            X = df[['day_of_year', 'year']]
            y = df['value']
            
            model = RandomForestRegressor(n_estimators=100)
            model.fit(X, y)
            
            # Future dates
            last_date = df['timestamp'].max()
            future_dates = [last_date + timedelta(days=i) for i in range(1, steps + 1)]
            X_future = pd.DataFrame({
                'day_of_year': [d.dayofyear for d in future_dates],
                'year': [d.year for d in future_dates]
            })
            
            preds = model.predict(X_future)
            return pd.Series(preds, index=future_dates)
        except Exception:
            return pd.Series(dtype=float)

    def forecast_gsri(self, steps: int = 7) -> Dict:
        """Forecast overall GSRI."""
        # Simple aggregate forecast:
        # 1. Get recent GSRI scores
        cur = self.conn.execute('SELECT calculation_timestamp, gsri_score FROM risk_calculations ORDER BY calculation_timestamp ASC')
        rows = cur.fetchall()
        if len(rows) < 5:
            return {"error": "Insufficient data"}
            
        df = pd.DataFrame(rows, columns=['timestamp', 'score'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        series = df.set_index('timestamp')['score']
        
        forecast = self.forecast_arima(series, steps=steps)
        
        return {
            "7d_forecast": round(forecast.iloc[-1], 2) if len(forecast) > 0 else 50.0,
            "method": "ARIMA"
        }

    def close(self):
        if self.conn:
            self.conn.close()
