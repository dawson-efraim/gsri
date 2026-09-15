# GSRI Configuration
# All data sources, indicators, update frequencies, and API endpoints

DATA_SOURCES = {
    "noaa_co2": {
        "name": "NOAA Global CO2",
        "base_url": "https://gml.noaa.gov/webdata/ccgg/trends/co2",
        "indicators": {
            "co2_daily": {
                "url": "co2_daily_mlo.csv",
                "frequency": "daily",
                "description": "Daily CO2 concentration at Mauna Loa",
                "unit": "ppm",
                "parser": "noaa_co2_csv"
            }
        }
    },
    "noaa_temperature": {
        "name": "NOAA Global Temperature",
        "base_url": "https://www.ncei.noaa.gov/data/global-summary-of-the-day/access",
        "indicators": {
            "global_temp_anomaly": {
                "url": "https://data.nodc.noaa.gov/c00004/ghcnm-v4/temperature-anomalies.csv",
                "frequency": "monthly",
                "description": "Global land-ocean temperature anomaly",
                "unit": "°C",
                "parser": "noaa_temp_csv"
            }
        }
    },
    "world_bank": {
        "name": "World Bank Open Data",
        "base_url": "https://api.worldbank.org/v2",
        "indicators": {
            "gdp_growth": {
                "series": "NY.GDP.MKTP.KD.ZG",
                "frequency": "annual",
                "description": "GDP growth (annual %)",
                "unit": "%",
                "parser": "worldbank_json"
            },
            "population": {
                "series": "SP.POP.TOTL",
                "frequency": "annual",
                "description": "Total population",
                "unit": "count",
                "parser": "worldbank_json"
            },
            "co2_emissions": {
                "series": "EN.ATM.CO2E.KT",
                "frequency": "annual",
                "description": "CO2 emissions (kt)",
                "unit": "kt",
                "parser": "worldbank_json"
            },
            "renewable_energy": {
                "series": "EG.FEC.RNEW.ZS",
                "frequency": "annual",
                "description": "Renewable energy consumption (% of total)",
                "unit": "%",
                "parser": "worldbank_json"
            },
            "food_production_index": {
                "series": "AG.PRD.FOOD.XD",
                "frequency": "annual",
                "description": "Food production index (2014-2016=100)",
                "unit": "index",
                "parser": "worldbank_json"
            },
            "arable_land": {
                "series": "AG.LND.ARBL.HA.PC",
                "frequency": "annual",
                "description": "Arable land (hectares per person)",
                "unit": "ha/person",
                "parser": "worldbank_json"
            },
            "freshwater_withdrawal": {
                "series": "ER.H2O.FWTL.ZS",
                "frequency": "annual",
                "description": "Annual freshwater withdrawals (% of internal resources)",
                "unit": "%",
                "parser": "worldbank_json"
            },
            "poverty_rate": {
                "series": "SI.POV.DDAY",
                "frequency": "annual",
                "description": "Poverty headcount ratio at $2.15/day",
                "unit": "%",
                "parser": "worldbank_json"
            },
            "gini_index": {
                "series": "SI.POV.GINI",
                "frequency": "annual",
                "description": "Gini index",
                "unit": "index",
                "parser": "worldbank_json"
            },
            "military_expenditure": {
                "series": "MS.MIL.XPND.GD.ZS",
                "frequency": "annual",
                "description": "Military expenditure (% of GDP)",
                "unit": "%",
                "parser": "worldbank_json"
            }
        }
    },
    "fao": {
        "name": "FAO Food Price Index",
        "base_url": "https://www.fao.org/worldfoodsituation/foodpricesindex/en",
        "indicators": {
            "food_price_index": {
                "url": "https://www.fao.org/worldfoodsituation/FoodPriceIndex_data.csv",
                "frequency": "monthly",
                "description": "FAO Food Price Index",
                "unit": "index",
                "parser": "fao_csv"
            }
        }
    },
    "usgs_earthquakes": {
        "name": "USGS Earthquake Feed",
        "base_url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary",
        "indicators": {
            "earthquakes_last_30d": {
                "url": "all_month.geojson",
                "frequency": "daily",
                "description": "Earthquakes magnitude 2.5+ in last 30 days",
                "unit": "count",
                "parser": "usgs_geojson"
            }
        }
    },
    "emdat": {
        "name": "EM-DAT Disaster Database",
        "base_url": "https://public.emdat.be",
        "indicators": {
            "disasters": {
                "frequency": "monthly",
                "description": "Natural disasters by type",
                "unit": "count",
                "parser": "emdat_api"
            }
        }
    },
    "gateway": {
        "name": "Commodity/Energy Gateway",
        "base_url": "https://api.marketdata.app/v1",
        "indicators": {
            "oil_price": {
                "symbol": "CL=F",
                "frequency": "hourly",
                "description": "WTI Crude Oil Price",
                "unit": "USD/barrel",
                "parser": "gateway_json"
            },
            "gas_price": {
                "symbol": "NG=F",
                "frequency": "hourly",
                "description": "Henry Hub Natural Gas Price",
                "unit": "USD/MMBtu",
                "parser": "gateway_json"
            }
        }
    }
}

# Indicator -> Risk Category Mapping
INDICATOR_CATEGORIES = {
    "co2_daily": "climate",
    "global_temp_anomaly": "climate",
    "co2_emissions": "climate",
    "renewable_energy": "energy",
    "food_price_index": "food",
    "food_production_index": "food",
    "arable_land": "food",
    "freshwater_withdrawal": "water",
    "population": "society",
    "gdp_growth": "economy",
    "poverty_rate": "society",
    "gini_index": "society",
    "military_expenditure": "geopolitics",
    "earthquakes_last_30d": "geopolitics",
    "oil_price": "energy",
    "gas_price": "energy"
}

# Risk Categories
RISK_CATEGORIES = [
    "climate", "water", "food", "energy",
    "biodiversity", "society", "economy", "geopolitics"
]

# Normalization bounds per indicator (min, max) for 0-100 scaling
NORMALIZATION_BOUNDS = {
    "co2_daily": (350, 500),  # ppm
    "global_temp_anomaly": (-0.5, 2.5),  # °C
    "co2_emissions": (0, 50000000),  # kt
    "renewable_energy": (0, 100),  # %
    "food_price_index": (50, 200),  # index
    "food_production_index": (50, 150),  # index
    "arable_land": (0.05, 0.5),  # ha/person
    "freshwater_withdrawal": (0, 100),  # %
    "population": (0, 10000000000),  # count
    "gdp_growth": (-10, 15),  # %
    "poverty_rate": (0, 80),  # %
    "gini_index": (20, 70),  # index
    "military_expenditure": (0, 10),  # %
    "earthquakes_last_30d": (0, 2000),  # count
    "oil_price": (20, 200),  # USD/barrel
    "gas_price": (1, 20)  # USD/MMBtu
}

# Direction: 1 = higher = more risk, -1 = higher = less risk
INDICATOR_DIRECTION = {
    "co2_daily": 1,
    "global_temp_anomaly": 1,
    "co2_emissions": 1,
    "renewable_energy": -1,  # more renewable = less risk
    "food_price_index": 1,
    "food_production_index": -1,  # more production = less risk
    "arable_land": -1,  # more land = less risk
    "freshwater_withdrawal": 1,
    "population": 1,
    "gdp_growth": -1,  # more growth = less risk (generally)
    "poverty_rate": 1,
    "gini_index": 1,
    "military_expenditure": 1,
    "earthquakes_last_30d": 1,
    "oil_price": 1,
    "gas_price": 1
}

# Weighting Methods
WEIGHTING_METHODS = {
    "expert": "Expert/theoretical weighting based on literature",
    "statistical": "Statistical weighting (variance-based)",
    "pca": "PCA-based weighting (first component loadings)",
    "equal": "Equal weighting across all indicators"
}

# Expert weights per category (sums to 1.0)
EXPERT_CATEGORY_WEIGHTS = {
    "climate": 0.25,
    "water": 0.15,
    "food": 0.15,
    "energy": 0.10,
    "biodiversity": 0.10,
    "society": 0.10,
    "economy": 0.10,
    "geopolitics": 0.05
}

# Alert thresholds
ALERT_THRESHOLDS = {
    "gsri_critical": 75,
    "gsri_high": 60,
    "gsri_elevated": 40,
    "momentum_rapid": 5,  # points per 30 days
    "category_spike": 15,  # points jump in single category
    "compound_min_categories": 3,
    "compound_min_increase": 5
}

# Database
DATABASE_PATH = "data/gsri.db"

# Cache
CACHE_DIR = "data/cache"
CACHE_TTL_HOURS = {
    "hourly": 1,
    "daily": 6,
    "weekly": 24,
    "monthly": 72,
    "quarterly": 168,
    "annual": 720
}

# Dashboard
DASHBOARD_REFRESH_SECONDS = 300  # 5 minutes