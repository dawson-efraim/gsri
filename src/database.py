"""SQLite storage for GSRI platform."""
import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple


class Database:
    def __init__(self, db_path: str = "data/gsri.db"):
        self.db_path = db_path
        self.conn = None
        self._connect()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()

    def _create_tables(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS data_sources (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                base_url TEXT,
                created_at TEXT,
                last_checked TEXT
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS indicators (
                id INTEGER PRIMARY KEY,
                source_id INTEGER,
                name TEXT,
                category TEXT,
                unit TEXT,
                frequency TEXT,
                bounds_min REAL,
                bounds_max REAL,
                direction INTEGER,
                created_at TEXT,
                FOREIGN KEY(source_id) REFERENCES data_sources(id)
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS data_points (
                id INTEGER PRIMARY KEY,
                indicator_id INTEGER,
                value REAL,
                timestamp TEXT,
                source_timestamp TEXT,
                is_valid INTEGER,
                FOREIGN KEY(indicator_id) REFERENCES indicators(id)
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS risk_calculations (
                id INTEGER PRIMARY KEY,
                calculation_timestamp TEXT,
                data_version TEXT,
                model_version TEXT,
                gsri_score REAL,
                weights_json TEXT,
                method TEXT
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY,
                alert_timestamp TEXT,
                severity TEXT,
                category TEXT,
                description TEXT,
                confidence REAL,
                data_point_ids TEXT
            )
        ''')
        self.conn.commit()

    def add_source(self, name: str, base_url: str):
        try:
            self.conn.execute(
                "INSERT INTO data_sources (name, base_url, created_at, last_checked) VALUES (?, ?, ?, ?)",
                (name, base_url, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def add_indicator(self, source_id: int, name: str, category: str, unit: str,
                      frequency: str, bounds_min: float = None,
                      bounds_max: float = None, direction: int = 1):
        self.conn.execute('''
            INSERT INTO indicators (source_id, name, category, unit, frequency,
                                    bounds_min, bounds_max, direction, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (source_id, name, category, unit, frequency, bounds_min,
              bounds_max, direction, datetime.utcnow().isoformat()))
        self.conn.commit()
        return True

    def add_data_point(self, indicator_id: int, value: float, timestamp: str,
                       source_timestamp: str, is_valid: int = 1):
        self.conn.execute('''
            INSERT INTO data_points (indicator_id, value, timestamp, source_timestamp, is_valid)
            VALUES (?, ?, ?, ?, ?)
        ''', (indicator_id, value, timestamp, source_timestamp, is_valid))
        self.conn.commit()
        return True

    def get_indicator_id(self, source_name: str, indicator_name: str) -> Optional[int]:
        cursor = self.conn.execute('''
            SELECT i.id FROM indicators i
            JOIN data_sources s ON i.source_id = s.id
            WHERE s.name = ? AND i.name = ?
        ''', (source_name, indicator_name))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_all_valid_data_points(self, indicator_id: int) -> List[Tuple[str, float]]:
        cursor = self.conn.execute('''
            SELECT timestamp, value FROM data_points
            WHERE indicator_id = ? AND is_valid = 1
            ORDER BY timestamp DESC
        ''', (indicator_id,))
        return cursor.fetchall()

    def update_last_checked(self, source_name: str, last_checked: str):
        self.conn.execute(
            "UPDATE data_sources SET last_checked = ? WHERE name = ?",
            (last_checked, source_name))
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
