import requests
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import math
import pandas as pd
import numpy as np

API = "https://services3.arcgis.com/zcv98lgAl8xQ04cW/ArcGIS/rest/services/Hourly_Ambient_Air_Quality/FeatureServer/0/query"
OUTPUT = Path("data/current_map.geojson")

# ---- TIME WINDOW (last 3 hours) ----
now_utc = datetime.now(timezone.utc)
cutoff = now_utc - timedelta(hours=96)

start_ms = int(cutoff.timestamp() * 1000)
end_ms = int(now_utc.timestamp() * 1000)

# ---- API REQUEST ----
r = requests.get(
    API,
    params={
        "time": f"{start_ms},{end_ms}",
        "outFields": "COMMUNITY,PM2_5,NO2,O3,WS,WD,TEMP,RH,DATETIME",
        "orderByFields": "COMMUNITY ASC, DATETIME DESC",
        "f": "geojson",
        "resultRecordCount": 5000
    }
)

print("Status:", r.status_code)

data = r.json()

if "features" not in data:
    print("API RESPONSE ERROR:")
    print(data)
    raise SystemExit("No features returned")

# ---- CLEANER ----
def clean_val(x):
    try:
        x = float(x)
        if x <= -999:
            return None
        return round(x, 1)
    except:
        return None

# ---- AQHI FUNCTION ----
def calc_aqhi(pm25, no2, o3):
    try:
        if None in [pm25, no2, o3]:
            return None

        aqhi = (10/10.4) * (100*(
            math.exp(0.000871 * no2) +
            math.exp(0.000537 * o3) +
            math.exp(0.000487 * pm25) - 3
        ))

        aqhi = round(aqhi)
        return max(1, min(10, aqhi))
    except:
        return None



# ---- BUILD DATAFRAME ----
rows = []

for f in data["features"]:

    p = f["properties"]

    pm25 = clean_val(p.get("PM2_5"))
    no2  = clean_val(p.get("NO2"))
    o3   = clean_val(p.get("O3"))

    rows.append({

        "station": p["COMMUNITY"],

        "datetime": datetime.fromtimestamp(
            p["DATETIME"]/1000,
            timezone.utc
        ),

        "PM25": pm25,
        "NO2": no2,
        "O3": o3,

        "WS": clean_val(p.get("WS")),
        "WD": clean_val(p.get("WD")),
        "TEMP": clean_val(p.get("TEMP")),
        "RH": clean_val(p.get("RH")),

        "AQHI": calc_aqhi(pm25, no2, o3),

        "geometry": f["geometry"]
    })

df = pd.DataFrame(rows)


# ---- SORT TEMPORALLY ----
df = df.sort_values(["station", "datetime"])


# ---- LAG FEATURES ----
df["AQHI_lag1"]  = df.groupby("station")["AQHI"].shift(1)
df["AQHI_lag2"]  = df.groupby("station")["AQHI"].shift(2)
df["AQHI_lag3"]  = df.groupby("station")["AQHI"].shift(3)
df["AQHI_lag6"]  = df.groupby("station")["AQHI"].shift(6)
df["AQHI_lag12"] = df.groupby("station")["AQHI"].shift(12)
df["AQHI_lag24"] = df.groupby("station")["AQHI"].shift(24)


# ---- CHANGE FEATURES ----
df["AQHI_change_1h"] = df["AQHI"] - df["AQHI_lag1"]
df["AQHI_change_3h"] = df["AQHI"] - df["AQHI_lag3"]


# ---- TEMPORAL FEATURES ----
df["hour"] = df["datetime"].dt.hour
df["doy"]  = df["datetime"].dt.dayofyear

df["sin_hour"] = np.sin(2*np.pi*df["hour"]/24)
df["cos_hour"] = np.cos(2*np.pi*df["hour"]/24)

df["sin_doy"] = np.sin(2*np.pi*df["doy"]/365)
df["cos_doy"] = np.cos(2*np.pi*df["doy"]/365)


# ---- REQUIRE COMPLETE LAG HISTORY ----
df = df.dropna(subset=[
    "AQHI_lag1",
    "AQHI_lag2",
    "AQHI_lag3",
    "AQHI_lag6",
    "AQHI_lag12",
    "AQHI_lag24"
])


# ---- KEEP LATEST FORECAST ROW ----
latest = df.groupby("station").tail(1)

# ---- SAVE FEATURE TABLE ----
latest.to_csv(
    "data/current_features.csv",
    index=False
)




# ---- FEATURE VALIDATION ----

print("\n=== FEATURE VALIDATION ===")

required = [
    "AQHI",
    "AQHI_lag1",
    "AQHI_lag2",
    "AQHI_lag3",
    "AQHI_lag6",
    "AQHI_lag12",
    "AQHI_lag24",
    "AQHI_change_1h",
    "AQHI_change_3h",
    "PM25",
    "O3",
    "NO2",
    "WS",
    "TEMP",
    "RH",
    "sin_hour",
    "cos_hour",
    "sin_doy",
    "cos_doy"
]

for c in required:

    if c not in latest.columns:
        print(f"MISSING COLUMN: {c}")
        continue

    print(
        f"{c:20s}",
        "dtype=", latest[c].dtype,
        "missing=", int(latest[c].isna().sum()),
        "sample=", latest[c].dropna().head(3).tolist()
    )

print("=== END FEATURE VALIDATION ===\n")





# ---- BUILD GEOJSON FEATURES ----
features = []

for _, row in latest.iterrows():

    feature = {
        "type": "Feature",

        "geometry": row["geometry"],

        "properties": {

            "station": row["station"],

            # Current AQHI
            "AQHI": row["AQHI"],

            # Pollutants
            "PM25": row["PM25"],
            "NO2": row["NO2"],
            "O3": row["O3"],

            # Weather
            "WS": row["WS"],
            "WD": row["WD"],
            "TEMP": row["TEMP"],
            "RH": row["RH"],

            # Lag features
            "AQHI_lag1": row["AQHI_lag1"],
            "AQHI_lag2": row["AQHI_lag2"],
            "AQHI_lag3": row["AQHI_lag3"],
            "AQHI_lag6": row["AQHI_lag6"],
            "AQHI_lag12": row["AQHI_lag12"],
            "AQHI_lag24": row["AQHI_lag24"],

            # Changes
            "AQHI_change_1h": row["AQHI_change_1h"],
            "AQHI_change_3h": row["AQHI_change_3h"],

            # Temporal terms
            "sin_hour": row["sin_hour"],
            "cos_hour": row["cos_hour"],
            "sin_doy": row["sin_doy"],
            "cos_doy": row["cos_doy"],

            # Timestamp
            "updated": row["datetime"].isoformat()
        }
    }

    features.append(feature)


# ---- OUTPUT ----
geojson = {
    "type": "FeatureCollection",
    "features": features
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT, "w") as f:
    json.dump(geojson, f)

print("Map features:", len(features))
