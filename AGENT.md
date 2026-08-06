# AGDFS — Agent Guide

This file is written for an AI agent (or any automated client) calling this API — either
via plain REST or via the MCP tools at `/mcp`. It covers what a docstring or OpenAPI
schema alone won't: units, sensible parameter choices, and mistakes that will silently
produce misleading results rather than an obvious error.

**Base URL:** `https://agdfs.onrender.com`

**Cold start:** this runs on a free-tier host that sleeps after inactivity. The first
request after idle time can take 30–50 seconds. If a request times out, retry once
before concluding the service is down.

---

## The four tools

| Tool / endpoint | Returns | Units |
|---|---|---|
| `get_satellite_imagery` / `GET /imagery` | List of Sentinel-2 scene metadata + preview links | Cloud cover in % |
| `get_elevation` / `GET /dem` | Elevation raster metadata (size, content-type) | Meters |
| `get_magnetic_anomaly` / `GET /geophysics/magnetic` | Grid of magnetic anomaly values | nanoTesla (nT) |
| `get_gravity_anomaly` / `GET /geophysics/gravity` | Grid of gravity anomaly values | milliGal (mGal) |
| `get_soil` / `GET /environment/soil` | Clay/sand/silt %, pH, organic carbon (0-5cm depth) | % and pH units |
| `get_weather` / `GET /environment/weather` | Current temperature, humidity, rainfall | °C, %, mm |
| `get_earthquakes` / `GET /environment/earthquakes` | Nearby seismic events | Magnitude, km depth |
| `get_air_quality` / `GET /environment/air-quality` | PM2.5, PM10, key pollutants, US AQI | µg/m³, AQI |

All four take `lat` and `lon` (WGS84 decimal degrees) as the point of interest, and a
`buffer_deg` controlling how wide an area around that point to return — **not** a radius
in kilometers, a difference in degrees of latitude/longitude.

---

## Choosing `buffer_deg` correctly

This is the most common way to get a technically-successful but practically useless
response. The right buffer size depends on the data's native resolution:

- **`/imagery`**: default `0.05` (~5km) is appropriate — Sentinel-2 is high-resolution (10m/pixel).
- **`/dem`**: default `0.1` (~11km) is reasonable for most elevation datasets (30m/pixel).
- **`/geophysics/magnetic`**: default `0.5` is intentional and should usually be kept —
  EMAG2v3 is a coarse ~2-arcminute grid. A smaller buffer doesn't give you more detail,
  it just returns fewer cells of the same coarse grid.
- **`/geophysics/gravity`**: default `0.5` for the same reason — WGM2012 is a 2-arcminute
  global grid. Requesting a very small buffer (e.g. `0.01`) will return a mostly-empty
  or single-cell result, not a higher-resolution answer.

**Rule of thumb:** shrinking `buffer_deg` below a dataset's native pixel size does not
increase precision — it just returns less data. If you need fine spatial detail,
`/imagery` or `/dem` are the right tools; the two geophysics endpoints are inherently
coarse, global-scale datasets.

---

## Reading gravity and magnetic responses correctly

Both `/geophysics/magnetic` and `/geophysics/gravity` return a 2D array under `"values"`
representing a grid, not a single number — even a small `buffer_deg` typically returns
many cells. If you only need one representative value for a point, use the returned
`"mean"` field rather than trying to pick a single cell out of `"values"` yourself,
since the exact cell closest to the requested point isn't guaranteed to be the first
one in the array.

**Sanity-check ranges** (useful for catching a malformed request or a genuinely unusual
result):
- Magnetic anomaly (`nT`): typically roughly -200 to +200 in most areas; larger
  magnitudes occur near strong crustal magnetic sources.
- Gravity anomaly (`mGal`): free-air and Bouguer values typically fall within roughly
  ±300 in most continental areas; the global extremes (close to -500/+1000) occur only
  in specific settings like major mountain belts or deep ocean trenches. A response
  where every value in the grid is identical, or where min/max are exactly 0, indicates
  something went wrong upstream — treat that as an error condition, not a valid flat
  region.

---

## `anomaly_type` on `/geophysics/gravity`

Two real, different physical quantities are available, not interchangeable:

- **`freeair`** (default) — gravity anomaly with only the elevation-based correction
  applied. Generally the better default for most exploration-style queries.
- **`bouguer`** — gravity anomaly with an additional correction that accounts for the
  gravitational effect of rock mass between the observation point and sea level.
  Prefer this when the analysis specifically concerns subsurface density variation
  independent of topography (e.g. looking for buried structures under varying terrain).

If a caller's request doesn't specify a reason to prefer one, default to `freeair`
rather than guessing.

---

## `demtype` on `/dem`

Multiple elevation datasets are available (`COP30`, `SRTMGL1`, `SRTMGL3`, `NASADEM`,
etc.) at different resolutions and with different global coverage gaps (e.g. some
datasets have limited coverage at high latitudes or over water). `COP30` (Copernicus
30m) is a reasonable general-purpose default. If a request fails or returns
unexpectedly sparse data, retrying with a different `demtype` is a reasonable fallback
before treating it as a hard failure.

---

## Error handling

- **`400`** — invalid parameter value (e.g. an unrecognized `anomaly_type`). Fix the
  request; retrying unchanged will not help.
- **`500`** — server misconfiguration (e.g. missing API key). Not something a
  different request will fix.
- **`502`** — the underlying data source (NOAA, Planetary Computer, etc.) failed or
  timed out. Safe to retry once; if it persists, the upstream source itself is likely
  degraded.

## What this API does not do

- It does not interpret or explain the data it returns — it hands back raw values.
  Any geological interpretation (e.g. "this magnetic signature suggests an intrusion")
  is the caller's responsibility, not something this API asserts.
- It does not store query history or user data between requests.
- It does not support write operations — every endpoint is read-only.
