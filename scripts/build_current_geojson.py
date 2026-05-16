import requests
import json
import math
from pathlib import Path
from datetime import datetime, timedelta, timezone

API = "https://services3.arcgis.com/zcv98lgAl8xQ04cW/ArcGIS/rest/services/Hourly_Ambient_Air_Quality/FeatureServer/0/query"
OUTPUT = Path("data/sk_aqhi_current.geojson")

# determine 3-hour cutoff
cutoff = datetime.now(timezone.utc) - timedelta(hours=3)
cutoff_ms = cutoff.timestamp() * 1000


# pull station data
r = requests.get(API, params={
    "where": "1=1",
    "outFields": "COMMUNITY,PM2_5,NO2,O3,WS,WD,TEMP,RH,DATETIME",
    "f": "geojson",
    "resultRecordCount": 1000
})

data = r.json()

if "features" not in data:
    print("ArcGIS error:")
    print(data)
    raise SystemExit


def calc_aqhi(PM25, NO2, O3):

    try:

        PM25 = float(PM25)
        NO2 = float(NO2)
        O3 = float(O3)

        if PM25 <= -999 or NO2 <= -999 or O3 <= -999:
            return None

        aqhi = (10/10.4) * (100*(
            math.exp(0.000871 * NO2) +
            math.exp(0.000537 * O3) +
            math.exp(0.000487 * PM25) - 3
        ))

        aqhi = round(aqhi)

        if aqhi < 1:
            aqhi = 1
        if aqhi > 10:
            aqhi = 10

        return aqhi

    except:
        return None


stations = {}

# collect station data within last 3 hours
for f in data["features"]:

    p = f["properties"]

    if p["DATETIME"] < cutoff_ms:
        continue

    station = p["COMMUNITY"]

    stations.setdefault(station, {
        "geometry": f["geometry"],
        "PM25": [],
        "NO2": [],
        "O3": [],
        "WS": [],
        "WD": [],
        "TEMP": [],
        "RH": [],        
        "times": []
    })

    stations[station]["PM25"].append(p.get("PM2_5"))
    stations[station]["NO2"].append(p.get("NO2"))
    stations[station]["O3"].append(p.get("O3"))
    stations[station]["WS"].append(p.get("WS"))    
    stations[station]["WD"].append(p.get("WD"))
    stations[station]["TEMP"].append(p.get("TEMP"))
    stations[station]["RH"].append(p.get("RH"))
    stations[station]["times"].append(p.get("DATETIME"))


features = []

for station, s in stations.items():

    PM25 = [v for v in s["PM25"] if v is not None and v > -999]
    NO2  = [v for v in s["NO2"] if v is not None and v > -999]
    O3   = [v for v in s["O3"] if v is not None and v > -999]
    
    WS   = [v for v in s["WS"] if v is not None and v > -999]
    WD   = [v for v in s["WD"] if v is not None and v > -999]
    TEMP = [v for v in s["TEMP"] if v is not None and v > -999]
    RH   = [v for v in s["RH"] if v is not None and v > -999]
    
    if not PM25 or not NO2 or not O3:
        continue

    PM25_avg = sum(PM25) / len(PM25)
    NO2_avg = sum(NO2) / len(NO2)
    O3_avg = sum(O3) / len(O3)

    aqhi = calc_aqhi(PM25_avg, NO2_avg, O3_avg)
    
    latest_idx = None
    
    for i in sorted(range(len(s["times"])), key=lambda x: s["times"][x], reverse=True):
        if (
            s["PM25"][i] is not None and s["PM25"][i] > -999 and
            s["NO2"][i] is not None and s["NO2"][i] > -999 and
            s["O3"][i] is not None and s["O3"][i] > -999
        ):
            latest_idx = i
            break
    
    if latest_idx is None:
        continue
    
    latest_time = s["times"][latest_idx]
    latest_dt = datetime.fromtimestamp(latest_time/1000, timezone.utc).isoformat()
      
    latest_PM25 = s["PM25"][latest_idx]
    latest_NO2 = s["NO2"][latest_idx]
    latest_O3 = s["O3"][latest_idx]
    
    latest_WS = s["WS"][latest_idx]
    latest_WD = s["WD"][latest_idx]
    latest_TEMP = s["TEMP"][latest_idx]
    latest_RH = s["RH"][latest_idx]    

    
    features.append({
        "type": "Feature",
        "geometry": s["geometry"],
        "properties": {
            "station": station,
            # latest hour (used by forecast model)
            "PM25": round(latest_PM25,1) if latest_PM25 is not None else None,
            "NO2": round(latest_NO2,1) if latest_NO2 is not None else None,
            "O3": round(latest_O3,1) if latest_O3 is not None else None,
            "WS": round(latest_WS,1) if latest_WS is not None else None,
            "WD": round(latest_WD,1) if latest_WD is not None else None,
            "TEMP": round(latest_TEMP,1) if latest_TEMP is not None else None,
            "RH": round(latest_RH,1) if latest_RH is not None else None,
            # 3-hour averages (used for AQHI)
            "PM25_3hr": round(PM25_avg,1),
            "NO2_3hr": round(NO2_avg,1),
            "O3_3hr": round(O3_avg,1),
        
            "AQHI": aqhi,
            "updated": latest_dt
        }
    })


geojson = {
    "type": "FeatureCollection",
    "features": features
}

OUTPUT.write_text(json.dumps(geojson, indent=2))

print("Stations processed:", len(features))
