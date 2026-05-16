import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import joblib
import os
os.makedirs("models", exist_ok=True)


# ---------------------------
# Load dataset
# ---------------------------
data = pd.read_csv("data/training_dataset.csv")
print("Rows:", len(data))
print("Columns:", data.columns)

# ---------------------------
# Targets (1 hour forecast)
# ---------------------------
data["PM25_target"] = data.groupby("station")["PM25"].shift(-1)
data["O3_target"] = data.groupby("station")["O3"].shift(-1)
data["NO2_target"] = data.groupby("station")["NO2"].shift(-1)

data = data.dropna()


# ---------------------------
# Feature columns
# ---------------------------
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


# ---------------------------
# Train function
# ---------------------------
def train_model(target, name):

    y = data[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=5,
        n_jobs=-1,
        random_state=42
    )

    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    print(f"{name} model R²:", score)
    joblib.dump(model, f"models/{name}_model.pkl")
    importance = pd.Series(
        model.feature_importances_,
        index=feature_cols
    ).sort_values(ascending=False)
    
    print(f"\nTop features for {name}:")
    print(importance.head(10))


# ---------------------------
# Train three models
# ---------------------------
train_model("PM25_target","pm25")
train_model("O3_target","o3")
train_model("NO2_target","no2")





