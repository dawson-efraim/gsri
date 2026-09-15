import pandas as pd
import requests
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.config import DATA_SOURCES, INDICATOR_CATEGORIES, NORMALIZATION_BOUNDS, INDICATOR_DIRECTION
from src.database import Database

class DataIngestion:
    def __init__(self, db_path: str = "data/gsri.db"):
        self.db = Database(db_path)
        self._initialize_metadata()
    
    def _initialize_metadata(self):
        for source_key, source_info in DATA_SOURCES.items():
            source_name = source_info["name"]
            base_url = source_info.get("base_url", "")
            self.db.add_source(source_name, base_url)
            
            # Get source_id
            cursor = self.db.conn.execute("SELECT id FROM data_sources WHERE name = ?", (source_name,))
            row = cursor.fetchone()
            if not row:
                continue
            source_id = row[0]
            
            for indicator_key, indicator_info in source_info.get("indicators", {}).items():
                category = INDICATOR_CATEGORIES.get(indicator_key, "society")
                unit = indicator_info.get("unit", "")
                frequency = indicator_info.get("frequency", "annual")
                bounds = NORMALIZATION_BOUNDS.get(indicator_key, (0, 100))
                direction = INDICATOR_DIRECTION.get(indicator_key, 1)
                
                # Check if indicator already exists
                ind_id = self.db.get_indicator_id(source_name, indicator_key)
                if not ind_id:
                    self.db.add_indicator(
                        source_id=source_id,
                        name=indicator_key,
                        category=category,
                        unit=unit,
                        frequency=frequency,
                        bounds_min=bounds[0],
                        bounds_max=bounds[1],
                        direction=direction
                    )
    
    def validate_data(self, indicator_name: str, value: float) -> bool:
        """Validate value against bounds and sanity checks."""
        bounds = NORMALIZATION_BOUNDS.get(indicator_name)
        if not bounds:
            return True
        
        b_min, b_max = bounds
        # Allow some margin beyond strict bounds for extreme values
        margin = (b_max - b_min) * 0.2
        
        if value < (b_min - margin) or value > (b_max + margin):
            return False
        
        if pd.isna(value) or not isinstance(value, (int, float)):
            return False
            
        return True
    
    def ingest_noaa_co2(self) -> int:
        """Fetch NOAA daily CO2 data."""
        source_name = "NOAA Global CO2"
        ind_key = "co2_daily"
        ind_id = self.db.get_indicator_id(source_name, ind_key)
        if not ind_id:
            return 0
            
        url = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_daily_mlo.csv"
        try:
            df = pd.read_csv(url, comment='#', header=None, names=['year', 'month', 'day', 'decimal_date', 'co2', 'days', 'std_dev', 'unc'])
            # Clean
            df = df[df['co2'] > 0]
            count = 0
            for _, row in df.tail(100).iterrows(): # Last 100 days
                val = float(row['co2'])
                timestamp = f"{int(row['year'])}:{int(row['month']):02d}:{int(row['day']):02d}"
                is_valid = 1 if self.validate_data(ind_key, val) else 0
                
                # Check if exists
                self.db.add_data_point(ind_id, val, timestamp, datetime.utcnow().isoformat(), is_valid)
                count += 1
            
            self.db.update_last_checked(source_name, datetime.utcnow().isoformat())
            return count
        except Exception as e:
            print(f"Error fetching NOAA CO2: {e}")
            return 0

    def ingest_world_bank(self) -> int:
        """Fetch World Bank indicators for global (WLD)."""
        source_name = "World Bank Open Data"
        indicators = DATA_SOURCES["world_bank"]["indicators"]
        count = 0
        
        for ind_key, info in indicators.items():
            ind_id = self.db.get_indicator_id(source_name, ind_key)
            if not ind_id:
                continue
                
            series = info["series"]
            url = f"https://api.worldbank.org/v2/country/WLD/indicator/{series}?format=json&per_page=20"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if len(data) > 1 and isinstance(data[1], list):
                        for entry in data[1]:
                            val = entry.get("value")
                            date = entry.get("date")
                            if val is not None and date is not None:
                                timestamp = f"{date}-01-01"
                                is_valid = 1 if self.validate_data(ind_key, float(val)) else 0
                                self.db.add_data_point(ind_id, float(val), timestamp, datetime.utcnow().isoformat(), is_valid)
                                count += 1
            except Exception as e:
                print(f"Error fetching WB {ind_key}: {e}")
                
        self.db.update_last_checked(source_name, datetime.utcnow().isoformat())
        return count

    def ingest_usgs_earthquakes(self) -> int:
        """Fetch USGS earthquakes feed."""
        source_name = "USGS Earthquake Feed"
        ind_key = "earthquakes_last_30d"
        ind_id = self.db.get_indicator_id(source_name, ind_key)
        if not ind_id:
            return 0
            
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                count = len(features)
                timestamp = datetime.utcnow().isoformat()[:10]
                is_valid = 1 if self.validate_data(ind_key, float(count)) else 0
                self.db.add_data_point(ind_id, float(count), timestamp, datetime.utcnow().isoformat(), is_valid)
                self.db.update_last_checked(source_name, datetime.utcnow().isoformat())
                return 1
        except Exception as e:
            print(f"Error fetching USGS: {e}")
        return 0

    def run_all(self):
        print("Running data ingestion pipeline...")
        c1 = self.ingest_noaa_co2()
        c2 = self.ingest_world_bank()
        c3 = self.ingest_usgs_earthquakes()
        print(f"Ingestion complete. Added {c1} CO2 records, {c2} World Bank records, {c3} USGS records.")

    def close(self):
        self.db.close()
