import pandas as pd
import numpy as np
import joblib
from datetime import datetime

# ----------------------------
# Load models
# ----------------------------
pm25_model = joblib.load("models/pm25_model.pkl")
o3_model   = joblib.load("models/o3_model.pkl")
no2_model  = joblib.load("models/no2_model.pkl")

# ----------------------------
# Load latest observations
# ----------------------------
data = pd.read_csv("data/latest_observations.csv")

# convert time
data["datetime"] = pd.to_datetime(data["datetime"])

# ----------------------------
# wind vectors
# ----------------------------
rad = np.deg2rad(data["WD"])
data["U"] = -data["WS"] * np.sin(rad)
data["V"] = -data["WS"] * np.cos(rad)

# ----------------------------
# time features
# ----------------------------
data["doy"] = data["datetime"].dt.dayofyear
data["hour"] = data["datetime"].dt.hour

data["sin_doy"] = np.sin(2*np.pi*data["doy"]/365)
data["cos_doy"] = np.cos(2*np.pi*data["doy"]/365)

data["sin_hour"] = np.sin(2*np.pi*data["hour"]/24)
data["cos_hour"] = np.cos(2*np.pi*data["hour"]/24)

# ----------------------------
# feature list (same as training)
# ----------------------------
feature_cols = [
"PM25_lag1","PM25_lag2","PM25_lag3","PM25_lag6","PM25_lag12",
"O3_lag1","O3_lag2","O3_lag3","O3_lag6","O3_lag12",
"NO2_lag1","NO2_lag2","NO2_lag3","NO2_lag6","NO2_lag12",
"WS","U","V","TEMP","RH",
"sin_hour","cos_hour",
"sin_doy","cos_doy",
"lat_norm","lon_norm","dist_center"
]

X = data[feature_cols]

# ----------------------------
# predictions
# ----------------------------
data["PM25_forecast"] = pm25_model.predict(X)
data["O3_forecast"]   = o3_model.predict(X)
data["NO2_forecast"]  = no2_model.predict(X)

# ----------------------------
# save forecast
# ----------------------------
data[[
"station",
"PM25_forecast",
"O3_forecast",
"NO2_forecast"
]].to_json("data/forecast.json", orient="records", indent=2)

print("Forecast generated")
