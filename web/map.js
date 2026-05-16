// create map
document.addEventListener("DOMContentLoaded", function () {

if (window.map) {
    window.map.remove();
}

var map = L.map("map").setView([52.5,-106],6);
    
window.map = map;

var stationLayer = L.layerGroup().addTo(map);
    

L.tileLayer(
"https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
{
attribution: "© OpenStreetMap"
}).addTo(map);



// FireSmoke layers (GeoJSON polygons)

function smokeStyle(feature){

  var v = feature.properties.pm25;

  if(v < 5)  return {fillColor:"#ffffcc", weight:0, color:"none", fillOpacity:0.5};
  if(v < 10) return {fillColor:"#ffeda0", weight:0, color:"none", fillOpacity:0.6};
  if(v < 25) return {fillColor:"#feb24c", weight:0, color:"none", fillOpacity:0.7};
  if(v < 50) return {fillColor:"#f03b20", weight:0, color:"none", fillOpacity:0.8};
  if(v < 100) return {fillColor:"#bd0026", weight:0, color:"none", fillOpacity:0.9};

  return {fillColor:"#800026", weight:0, color:"none", fillOpacity:0.95};
}

function loadSmokeLayer(url){

  var layer = L.layerGroup();

  fetch(url + "?v=" + Date.now())
  .then(r => r.json())
  .then(data => {

    L.geoJSON(data,{
      style: smokeStyle,
      onEachFeature:function(feature,layer){

        var v = feature.properties.pm25;

        layer.bindTooltip(
          "Smoke PM2.5: " + v + " µg/m³"
        );

      }
    }).addTo(layer);

  });

  return layer;
}

var smoke0 = loadSmokeLayer(
"https://dkevinm.github.io/SK_Air_Map/data/firesmoke_now.geojson"
);
var smoke6 = loadSmokeLayer(
"https://dkevinm.github.io/SK_Air_Map/data/firesmoke_6h.geojson"
);
var smoke12 = loadSmokeLayer(
"https://dkevinm.github.io/SK_Air_Map/data/firesmoke_12h.geojson"
);
var smoke24 = loadSmokeLayer(
"https://dkevinm.github.io/SK_Air_Map/data/firesmoke_24h.geojson"
);



var pm25Layer = loadPM25Layer(
  "https://raw.githubusercontent.com/dkevinm/AB_datapull/main/dataSK/SK_PM25_map.json"
);
   
var overlays = {
  "Smoke Now": smoke0,
  "Smoke +6 hr": smoke6,
  "Smoke +12 hr": smoke12,
  "Smoke +24 hr": smoke24,
  "PM2.5 Sensors": pm25Layer
};


L.control.layers(null, overlays, { position: "topright" }).addTo(map);




    

function getPMColor(pm){

  if(pm == null || isNaN(pm)) return "#808080";

  if (pm > 100) return "#640100";
  if (pm > 90)  return "#9a0100";
  if (pm > 80)  return "#cc0001";
  if (pm > 70)  return "#fe0002";
  if (pm > 60)  return "#fd6866";
  if (pm > 50)  return "#ff9835";
  if (pm > 40)  return "#ffcb00";
  if (pm > 30)  return "#fffe03";
  if (pm > 20)  return "#016797";
  if (pm > 10)  return "#0099cb";
  if (pm > 0)   return "#01cbff";

  return "#D3D3D3";
}

function pm25Style(feature){

  const v = feature.properties.pm25;

  return {
    fillColor: getPMColor(v),
    weight: 0.2,
    color: "#333",
    fillOpacity: 0.7
  };
}


function loadPM25Layer(url){

  var layer = L.layerGroup();

  fetch(url + "?v=" + Date.now())
  .then(r => r.json())
  .then(data => {

    console.log("PM25 features:", data.features?.length);

    L.geoJSON(data,{

      pointToLayer: function(feature, latlng){

        const p = feature.properties || {};
        const pm = p.pm25;

        return L.circleMarker(latlng, {
          radius: 6,
          fillColor: getPMColor(pm),
          color: "#333",
          weight: 1,
          fillOpacity: 0.8
        });

      },

      onEachFeature:function(feature,layer){

        const p = feature.properties || {};

        layer.bindPopup(`
          <b>${p.name ?? "Sensor"}</b><br>
          PM2.5: ${p.pm25 ?? "N/A"} µg/m³<br>
          Raw: ${p.pm_raw ?? "N/A"}<br>
          Humidity: ${p.humidity ?? "N/A"}%<br>
          Method: ${p.method ?? "N/A"}<br>
          Last Seen: ${p.last_seen ? new Date(p.last_seen).toLocaleString() : "N/A"}
        `);

      }

    }).addTo(layer);

  });

  return layer;
}


    

    
    
// Saskatchewan air monitoring API
var api =
"https://services3.arcgis.com/zcv98lgAl8xQ04cW/ArcGIS/rest/services/Hourly_Ambient_Air_Quality/FeatureServer/0/query?where=1=1&outFields=*&f=geojson";



    

// AQHI colors
function aqhiColor(v){

  if(v == null) return "#D3D3D3";

  if (v < 1)  return "#D3D3D3";
  if (v === 1) return "#01cbff";
  if (v === 2) return "#0099cb";
  if (v === 3) return "#016797";
  if (v === 4) return "#fffe03";
  if (v === 5) return "#ffcb00";
  if (v === 6) return "#ff9835";
  if (v === 7) return "#fd6866";
  if (v === 8) return "#fe0002";
  if (v === 9) return "#cc0001";
  if (v === 10) return "#9a0100";
  return "#640100";
}
    

function round1(v){
  if (v == null) return "N/A";
  return Number(v).toFixed(1);
}    



   

    
    
var aqhiLookup = {};
fetch("data/sk_aqhi_current.geojson")
.then(r => r.json())
.then(data => {
  data.features.forEach(f => {
    var p = f.properties;

    aqhiLookup[p.station.toUpperCase()] = {
      aqhi: Number(p.AQHI),
      time: p.updated
    };

  });

  console.log("AQHI lookup table:", aqhiLookup);

  loadStations();
});

    


    
// load stations
function loadStations(){
stationLayer.clearLayers();
fetch(api)
.then(r => r.json())
.then(data => {

  console.log("Stations returned:", data.features.length);

  var clean = data.features.filter(f => {

      if (!f.geometry) return false;
      if (!f.geometry.coordinates) return false;

      const lon = f.geometry.coordinates[0];
      const lat = f.geometry.coordinates[1];

      if (lon === null || lat === null) return false;
      if (isNaN(lon) || isNaN(lat)) return false;

      return true;

  });

  L.geoJSON(clean, {

    pointToLayer: function(feature,latlng){

      var p = feature.properties;

      var aqhiData = aqhiLookup[p.COMMUNITY.toUpperCase()];

      var aqhi = aqhiData ? aqhiData.aqhi : null;
      var aqhiTime = aqhiData ? new Date(aqhiData.time).toLocaleString() : "N/A";

      var color = aqhiColor(aqhi);
        
      var icon = L.divIcon({
        className: "aqhi-marker",
        html:
          "<div style='background:"+color+"'>"+
          (aqhi ?? "")+
          "</div>",
        iconSize: [38,38]
      });
        
      console.log(p.COMMUNITY, aqhiLookup[p.COMMUNITY.toUpperCase()]);  
      return L.marker(latlng,{icon:icon});

    },

    onEachFeature:function(feature,layer){

      var p = feature.properties;

      var aqhiData = aqhiLookup[p.COMMUNITY.toUpperCase()];

      var aqhi = aqhiData ? aqhiData.aqhi : null;
      var aqhiTime = aqhiData ? new Date(aqhiData.time).toLocaleString() : "N/A";

      var time = new Date(p.DATETIME).toLocaleString();

      layer.bindPopup(
        "<b>"+p.COMMUNITY+"</b><br>"+
        "AQHI (3hr): "+(aqhi ?? "N/A")+"<br>"+
        "<hr>"+
        "PM2.5: "+round1(p.PM2_5)+" µg/m³<br>"+
        "NO₂: "+round1(p.NO2)+" ppb<br>"+
        "O₃: "+round1(p.O3)+" ppb<br>"+
        "Wind: "+round1(p.WS)+" km/h<br>"+
        "Temp: "+round1(p.TEMP)+" °C<br>"+
        "<hr>"+
        "Station time: "+time+"<br>"+
        "AQHI updated: "+aqhiTime
      );

    }

  }).addTo(stationLayer);


});
}
});
