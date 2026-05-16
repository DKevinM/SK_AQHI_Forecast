import pandas as pd
import numpy as np
import glob
from pathlib import Path

DATA_DIR = Path("dataSK")

files = glob.glob(str(DATA_DIR / "*.csv"))

dfs = []

for f in files:

    df = pd.read_csv(f, sep=None, engine="python")

    print(df.columns)
    
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.replace(-9999, np.nan, inplace=True)
    dfs.append(df)


# ----------------------------------
# Load station metadata
# ----------------------------------
stations = pd.read_csv("data/stations.csv")


# ----------------------------
# combine stations
# ----------------------------
data = pd.concat(dfs)


# ----------------------------------
# Merge station coordinates
# ----------------------------------
data = data.merge(stations, on="station", how="left")

data["station"] = data["station"].astype(int)

data = data.sort_values(["station","datetime"])

print(data["station"].unique())
print(data[["station","name"]].drop_duplicates())

# ------------------------------------
# Fill small gaps (max 3 hours)
# ------------------------------------
cols = ["PM25","NO2","O3","WS","WD","TEMP","RH"]
for c in cols:
    data[c] = data.groupby("station")[c].transform(
        lambda x: x.interpolate(limit=3, limit_direction="both")
    )



# ------------------------------------------------
# WIND VECTOR FEATURES
# ------------------------------------------------
rad = np.deg2rad(data["WD"])

data["U"] = -data["WS"] * np.sin(rad)
data["V"] = -data["WS"] * np.cos(rad)


# ----------------------------------
# Wind transport proxy
# ----------------------------------
# difference from network centre
data["dlat"] = data["lat"] - data["lat"].mean()
data["dlon"] = data["lon"] - data["lon"].mean()

# transport index
data["transport_index"] = data["U"] * data["dlat"] + data["V"] * data["dlon"]


# ------------------------------------------------
# Normalize lat and lon
# ------------------------------------------------
data["lat_norm"] = (data["lat"] - data["lat"].mean()) / data["lat"].std()
data["lon_norm"] = (data["lon"] - data["lon"].mean()) / data["lon"].std()

data["dist_center"] = np.sqrt(
    (data["lat"] - data["lat"].mean())**2 +
    (data["lon"] - data["lon"].mean())**2
)



# ------------------------------------------------
# TIME FEATURES (seasonality)
# ------------------------------------------------
# day of year (seasonality)
data["doy"] = data["datetime"].dt.dayofyear
data["sin_doy"] = np.sin(2*np.pi*data["doy"]/365)
data["cos_doy"] = np.cos(2*np.pi*data["doy"]/365)

# hour of day (diurnal cycle)
data["hour"] = data["datetime"].dt.hour
data["sin_hour"] = np.sin(2*np.pi*data["hour"]/24)
data["cos_hour"] = np.cos(2*np.pi*data["hour"]/24)


# ----------------------------
# sort data before lagging
# ----------------------------
data = data.sort_values(["station", "datetime"])


# ------------------------------------------------
# LAG FEATURES
# ------------------------------------------------
for lag in [1,2,3,6,12,24]:

    data[f"PM25_lag{lag}"] = data.groupby("station")["PM25"].shift(lag)
    data[f"O3_lag{lag}"] = data.groupby("station")["O3"].shift(lag)
    data[f"NO2_lag{lag}"] = data.groupby("station")["NO2"].shift(lag)


# ------------------------------------------------
# 3-hour rolling averages
# ------------------------------------------------
data["pm25_3hr"] = data.groupby("station")["PM25"].rolling(3).mean().reset_index(level=0,drop=True)
data["o3_3hr"] = data.groupby("station")["O3"].rolling(3).mean().reset_index(level=0,drop=True)
data["no2_3hr"] = data.groupby("station")["NO2"].rolling(3).mean().reset_index(level=0,drop=True)


# ------------------------------------------------
# Remove incomplete rows
# ------------------------------------------------
data = data.dropna()


# ------------------------------------------------
# Save dataset
# ------------------------------------------------
data.to_csv("data/training_dataset.csv",index=False)
print("Training dataset built")


