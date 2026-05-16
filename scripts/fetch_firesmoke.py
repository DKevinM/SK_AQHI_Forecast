import requests
import xarray as xr
import numpy as np
import json
from pathlib import Path
import urllib3
from datetime import datetime, timedelta


urllib3.disable_warnings()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# region of interest (Prairies / Saskatchewan focus)
LAT_MIN = 42   # down into northern US
LAT_MAX = 65   # mid NWT
LON_MIN = -130 # BC coast-ish
LON_MAX = -90  # Manitoba east

url = "https://services.firesmoke.ca/forecasts/current/dispersion.nc"
nc_file = DATA_DIR / "firesmoke.nc"

print("Downloading FireSmoke forecast...")

r = requests.get(url, verify=False, timeout=120)

with open(nc_file, "wb") as f:
    f.write(r.content)

print("Saved:", nc_file)

ds = xr.open_dataset(nc_file)
print(ds)

tflag = ds["TFLAG"].values
date = int(tflag[0, 0, 0])
time = int(tflag[0, 0, 1])
year = date // 1000
day = date % 1000
hour = time // 10000
minute = (time % 10000) // 100
second = time % 100
smoke_time = datetime(year, 1, 1) + timedelta(days=day-1)
smoke_time = smoke_time.replace(hour=hour, minute=minute, second=second)
print("FireSmoke timestamp:", smoke_time)

pm = ds["PM25"]

# Downsample step
STEP = 3

forecast_hours = {
    "now":0,
    "6h":6,
    "12h":12,
    "24h":24
}

# grid size
rows = pm.shape[2]
cols = pm.shape[3]

# approximate geographic bounds of the grid
lon_min, lon_max = -145, -85
lat_min, lat_max = 35, 75

lon_step = (lon_max - lon_min) / cols
lat_step = (lat_max - lat_min) / rows



# Precompute lat/lon centers once
lat_vals = lat_min + np.arange(rows) * lat_step
lon_vals = lon_min + np.arange(cols) * lon_step

# Region mask once
region_mask = (
    (lat_vals[:, None] >= LAT_MIN) &
    (lat_vals[:, None] <= LAT_MAX) &
    (lon_vals[None, :] >= LON_MIN) &
    (lon_vals[None, :] <= LON_MAX)
)



for name, t in forecast_hours.items():

    forecast_time = smoke_time + timedelta(hours=t)
    print("Processing:", name, forecast_time)

    if t >= pm.shape[0]:
        print(f"Skipping {name} — not available")
        continue
    
    grid = pm.isel(TSTEP=t, LAY=0).values
    grid = np.flipud(grid)

    grid_ds = grid[::STEP, ::STEP]
    lat_ds = lat_vals[::STEP]
    lon_ds = lon_vals[::STEP]
    region_mask_ds = region_mask[::STEP, ::STEP]

    valid_mask = (~np.isnan(grid_ds)) & (grid_ds >= 0.5) & region_mask_ds
    valid_rc = np.argwhere(valid_mask)

    features = []

    for r_idx, c_idx in valid_rc:
        value = float(grid_ds[r_idx, c_idx])
        lat = lat_ds[r_idx]
        lon = lon_ds[c_idx]

        
        raw_val = float(grid_ds[r_idx, c_idx])
        
        
        "properties": {
            "pm25": raw_val,
            "forecast": name,
            "timestamp": forecast_time.isoformat()
        }    

            
        poly = [
            [lon, lat],
            [lon + lon_step * STEP * 1.02, lat],
            [lon + lon_step * STEP * 1.02, lat + lat_step * STEP * 1.02],
            [lon, lat + lat_step * STEP * 1.02],
            [lon, lat]
        ]

        features.append({
            "type": "Feature",
            "properties": {
                "pm25": float(value),
                "forecast": name,
                "timestamp": forecast_time.isoformat()
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [poly]
            }
        })

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    outfile = DATA_DIR / f"firesmoke_{name}.geojson"

    with open(outfile, "w") as f:
        json.dump(geojson, f)

    print("Saved:", outfile, "features:", len(features), "time:", forecast_time)
