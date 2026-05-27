import json
        "forecast_aqhi": "aqhi"
    })[["lat", "lon", "aqhi", "weight"]],
    sensors
], ignore_index=True)

features_forecast = []

for x in xs:

    for y in ys:

        dist = haversine(
            REGINA_LAT,
            REGINA_LON,
            y,
            x
        )

        if dist > MAX_DIST_KM:
            continue

        z = idw_interpolate(
            forecast_pts["lon"].values,
            forecast_pts["lat"].values,
            forecast_pts["aqhi"].values,
            forecast_pts["weight"].values,
            np.array([x]),
            np.array([y]),
            power=IDW_POWER
        )[0]

        poly = Polygon([
            (x - GRID_STEP_DEG/2, y - GRID_STEP_DEG/2),
            (x + GRID_STEP_DEG/2, y - GRID_STEP_DEG/2),
            (x + GRID_STEP_DEG/2, y + GRID_STEP_DEG/2),
            (x - GRID_STEP_DEG/2, y + GRID_STEP_DEG/2)
        ])

        features_forecast.append({
            "type": "Feature",
            "geometry": poly.__geo_interface__,
            "properties": {
                "AQHI": round(float(z), 1),
                "color": get_aqhi_color(z),
                "type": "forecast"
            }
        })

# =========================================================
# SAVE OUTPUTS
# =========================================================

current_geojson = {
    "type": "FeatureCollection",
    "features": features_current
}

forecast_geojson = {
    "type": "FeatureCollection",
    "features": features_forecast
}

with open(OUTPUT_CURRENT, "w") as f:
    json.dump(current_geojson, f)

with open(OUTPUT_FORECAST, "w") as f:
    json.dump(forecast_geojson, f)

print("Saved:")
print(OUTPUT_CURRENT)
print(OUTPUT_FORECAST)

print("DONE")
