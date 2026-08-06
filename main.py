"""
main.py

Unified geoscience data API. Each endpoint follows the same pattern:
call/clip from the source that already hosts the data, return a small
normalized response. Nothing large is stored on this server except the
cached geophysics grids (see geophysics.py), which are static and modest
in size.
"""

import os
from fastapi import FastAPI, HTTPException, Query
import requests

from geophysics import clip_magnetic, clip_gravity

app = FastAPI(
    title="AGDFS — Automated Geological Data Fetching System",
    description="Unified access to satellite imagery, elevation, and geophysics data for AI training and geological analysis.",
    version="0.1.0",
)

OPENTOPO_API_KEY = os.environ.get("OPENTOPO_API_KEY", "")
PLANETARY_COMPUTER_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
OPENTOPO_URL = "https://portal.opentopography.org/API/globaldem"


@app.get("/")
def root():
    return {
        "service": "AGDFS — Automated Geological Data Fetching System",
        "endpoints": ["/imagery", "/dem", "/geophysics/magnetic", "/geophysics/gravity", "/environment/soil", "/environment/weather", "/environment/earthquakes", "/environment/air-quality"],
        "docs": "/docs",
    }


@app.get("/imagery", operation_id="get_satellite_imagery")
def get_imagery(
    lat: float = Query(..., description="Latitude of point of interest"),
    lon: float = Query(..., description="Longitude of point of interest"),
    date_from: str = Query(..., description="Start date, YYYY-MM-DD"),
    date_to: str = Query(..., description="End date, YYYY-MM-DD"),
    buffer_deg: float = Query(0.05, description="Bounding box half-width in degrees"),
    limit: int = Query(5, le=20),
):
    bbox = [lon - buffer_deg, lat - buffer_deg, lon + buffer_deg, lat + buffer_deg]
    try:
        resp = requests.post(
            PLANETARY_COMPUTER_STAC,
            json={
                "collections": ["sentinel-2-l2a"],
                "bbox": bbox,
                "datetime": f"{date_from}/{date_to}",
                "limit": limit,
            },
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Imagery source unavailable: {e}")

    items = resp.json().get("features", [])
    return {
        "count": len(items),
        "results": [
            {
                "date": i["properties"].get("datetime"),
                "cloud_cover": i["properties"].get("eo:cloud_cover"),
                "preview_url": i.get("assets", {}).get("visual", {}).get("href"),
            }
            for i in items
        ],
    }


@app.get("/dem", operation_id="get_elevation")
def get_dem(
    lat: float = Query(..., description="Latitude of point of interest"),
    lon: float = Query(..., description="Longitude of point of interest"),
    buffer_deg: float = Query(0.1, description="Bounding box half-width in degrees"),
    demtype: str = Query("COP30", description="e.g. SRTMGL1, SRTMGL3, COP30, NASADEM"),
):
    if not OPENTOPO_API_KEY:
        raise HTTPException(status_code=500, detail="OPENTOPO_API_KEY not configured on server")

    params = {
        "demtype": demtype,
        "south": lat - buffer_deg,
        "north": lat + buffer_deg,
        "west": lon - buffer_deg,
        "east": lon + buffer_deg,
        "outputFormat": "GTiff",
        "API_Key": OPENTOPO_API_KEY,
    }
    try:
        resp = requests.get(OPENTOPO_URL, params=params, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"DEM source unavailable: {e}")

    return {
        "demtype": demtype,
        "bounds": {k: params[k] for k in ("south", "north", "west", "east")},
        "content_type": resp.headers.get("Content-Type"),
        "size_bytes": len(resp.content),
        "note": "Raw GeoTIFF bytes available via a streaming variant of this endpoint; this response returns metadata only.",
    }


@app.get("/geophysics/magnetic", operation_id="get_magnetic_anomaly")
def get_magnetic(
    lat: float = Query(..., description="Latitude of point of interest"),
    lon: float = Query(..., description="Longitude of point of interest"),
    buffer_deg: float = Query(0.5, description="Magnetic anomaly grids are coarse (~2 arcmin); use a wider buffer than imagery/DEM"),
):
    try:
        result = clip_magnetic(
            south=lat - buffer_deg, north=lat + buffer_deg,
            west=lon - buffer_deg, east=lon + buffer_deg,
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"NOAA EMAG2v3 service unavailable: {e}")
    return result


@app.get("/geophysics/gravity", operation_id="get_gravity_anomaly")
def get_gravity(
    lat: float = Query(..., description="Latitude of point of interest"),
    lon: float = Query(..., description="Longitude of point of interest"),
    buffer_deg: float = Query(0.5, description="Bounding box half-width in degrees"),
    anomaly_type: str = Query("freeair", description="'freeair' or 'bouguer'"),
):
    try:
        result = clip_gravity(
            south=lat - buffer_deg, north=lat + buffer_deg,
            west=lon - buffer_deg, east=lon + buffer_deg,
            anomaly_type=anomaly_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gravity COG unavailable: {e}")
    return result


@app.get("/environment/soil", operation_id="get_soil")
def get_soil(
    lat: float = Query(..., description="Latitude of point of interest"),
    lon: float = Query(..., description="Longitude of point of interest"),
):
    """Soil composition at a point (0-5cm depth), via ISRIC SoilGrids, live query."""
    params = {
        "lat": lat, "lon": lon, "depth": "0-5cm", "value": "mean",
        "property": ["clay", "sand", "silt", "phh2o", "soc"],
    }
    try:
        resp = requests.get("https://rest.isric.org/soilgrids/v2.0/properties/query", params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"ISRIC SoilGrids unavailable: {e}")

    layers = resp.json().get("properties", {}).get("layers", [])

    def value_for(name):
        for layer in layers:
            if layer.get("name") == name:
                depths = layer.get("depths", [])
                return depths[0]["values"].get("mean") if depths else None
        return None

    return {
        "source": "ISRIC SoilGrids (0-5cm depth, live query, no caching)",
        "lat": lat, "lon": lon,
        "clay_pct": value_for("clay"), "sand_pct": value_for("sand"), "silt_pct": value_for("silt"),
        "ph": value_for("phh2o"), "organic_carbon": value_for("soc"),
    }


@app.get("/environment/weather", operation_id="get_weather")
def get_weather(
    lat: float = Query(..., description="Latitude of point of interest"),
    lon: float = Query(..., description="Longitude of point of interest"),
):
    """Current rainfall, temperature, and humidity at a point, via Open-Meteo, live query."""
    params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,rain",
    }
    try:
        resp = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Open-Meteo weather unavailable: {e}")

    data = resp.json().get("current", {})
    return {
        "source": "Open-Meteo (live query, no caching)",
        "lat": lat, "lon": lon,
        "temperature_c": data.get("temperature_2m"),
        "humidity_pct": data.get("relative_humidity_2m"),
        "precipitation_mm": data.get("precipitation"),
        "rain_mm": data.get("rain"),
    }


@app.get("/environment/earthquakes", operation_id="get_earthquakes")
def get_earthquakes(
    lat: float = Query(..., description="Latitude of point of interest"),
    lon: float = Query(..., description="Longitude of point of interest"),
    buffer_deg: float = Query(1.0, description="Bounding box half-width in degrees"),
    days: int = Query(30, description="How many days back to search"),
    min_magnitude: float = Query(2.5, description="Minimum earthquake magnitude to include"),
):
    """Recent seismic activity near a point, via USGS's live earthquake catalog."""
    from datetime import datetime, timedelta, timezone
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    params = {
        "format": "geojson",
        "starttime": start.strftime("%Y-%m-%d"),
        "endtime": end.strftime("%Y-%m-%d"),
        "minlatitude": lat - buffer_deg, "maxlatitude": lat + buffer_deg,
        "minlongitude": lon - buffer_deg, "maxlongitude": lon + buffer_deg,
        "minmagnitude": min_magnitude,
    }
    try:
        resp = requests.get("https://earthquake.usgs.gov/fdsnws/event/1/query", params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"USGS earthquake service unavailable: {e}")

    features = resp.json().get("features", [])
    return {
        "count": len(features),
        "source": "USGS Earthquake Catalog (live query, no caching)",
        "results": [
            {
                "magnitude": f["properties"].get("mag"),
                "place": f["properties"].get("place"),
                "time": f["properties"].get("time"),
                "depth_km": f["geometry"]["coordinates"][2] if f.get("geometry") else None,
                "lat": f["geometry"]["coordinates"][1] if f.get("geometry") else None,
                "lon": f["geometry"]["coordinates"][0] if f.get("geometry") else None,
            }
            for f in features
        ],
    }


@app.get("/environment/air-quality", operation_id="get_air_quality")
def get_air_quality(
    lat: float = Query(..., description="Latitude of point of interest"),
    lon: float = Query(..., description="Longitude of point of interest"),
):
    """Current air quality (PM2.5, PM10, and key pollutants) via Open-Meteo, live query."""
    params = {
        "latitude": lat, "longitude": lon,
        "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi",
    }
    try:
        resp = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality", params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Open-Meteo air quality service unavailable: {e}")

    data = resp.json().get("current", {})
    return {
        "source": "Open-Meteo Air Quality (live query, no caching)",
        "lat": lat, "lon": lon,
        "pm2_5": data.get("pm2_5"), "pm10": data.get("pm10"),
        "carbon_monoxide": data.get("carbon_monoxide"),
        "nitrogen_dioxide": data.get("nitrogen_dioxide"),
        "sulphur_dioxide": data.get("sulphur_dioxide"),
        "ozone": data.get("ozone"),
        "us_aqi": data.get("us_aqi"),
    }


from fastapi.responses import RedirectResponse

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse("https://i.ibb.co/DPwRdz8g/file-00000000ab4c8243824cc698b7da8db9.png")


# --- MCP layer -------------------------------------------------------
# Wraps the REST endpoints above as MCP tools with no duplicated logic --
# any MCP-compatible agent can call the same operations through the
# /mcp route instead of individual GET requests.
from fastapi_mcp import FastApiMCP

mcp = FastApiMCP(
    app,
    name="AGDFS",
    description="Automated Geological Data Fetching System — satellite imagery, elevation, and geophysics data for any coordinate on Earth.",
)
mcp.mount_http()
