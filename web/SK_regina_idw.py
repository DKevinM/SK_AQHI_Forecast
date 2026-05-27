import json

sensors = pd.DataFrame(sensors)

# =====================================================
# COMBINE
# =====================================================

allpts = pd.concat([stations, sensors], ignore_index=True)

# =====================================================
# REGINA BUFFER
# =====================================================

xmin = REGINA_LON - 1.4
xmax = REGINA_LON + 1.4

ymin = REGINA_LAT - 0.9
ymax = REGINA_LAT + 0.9

# =====================================================
# GRID
# =====================================================

xs = np.arange(xmin, xmax, 0.05)
ys = np.arange(ymin, ymax, 0.05)

features = []

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

        z = idw(
            allpts["lon"].values,
            allpts["lat"].values,
            allpts["aqhi"].values,
            allpts["weight"].values,
            np.array([x]),
            np.array([y])
        )[0]

        poly = Polygon([
            (x-0.025, y-0.025),
            (x+0.025, y-0.025),
            (x+0.025, y+0.025),
            (x-0.025, y+0.025)
        ])

        features.append({
            "type": "Feature",
            "geometry": poly.__geo_interface__,
            "properties": {
                "AQHI": round(float(z), 1),
                "color": get_aqhi_color(z)
            }
        })

# =====================================================
# SAVE CURRENT GRID
# =====================================================

geojson = {
    "type": "FeatureCollection",
    "features": features
}

with open("data/regina_current_blend.geojson", "w") as f:
    json.dump(geojson, f)

print("Saved current grid")
