<p align="center">
  <img src="https://i.ibb.co/N22tsCsQ/file-000000004a4881f49dcb347ec9ac082e.png" alt="AGDFS Banner" width="100%">
</p>

<h1 align="center">AGDFS</h1>
<h3 align="center">Automated Geological Data Fetching System</h3>

<p align="center">
  <img src="https://img.shields.io/github/license/Nora-Research-Lab/AGDFS" alt="license">
  <img src="https://img.shields.io/github/contributors/Nora-Research-Lab/AGDFS" alt="contributors">
  <img src="https://img.shields.io/github/issues/Nora-Research-Lab/AGDFS" alt="issues">
  <img src="https://img.shields.io/github/issues-pr/Nora-Research-Lab/AGDFS" alt="pull requests">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs welcome">
</p>
<p align="center">
  <img src="https://img.shields.io/github/watchers/Nora-Research-Lab/AGDFS?style=social" alt="watch">
  <img src="https://img.shields.io/github/forks/Nora-Research-Lab/AGDFS?style=social" alt="fork">
  <img src="https://img.shields.io/github/stars/Nora-Research-Lab/AGDFS?style=social" alt="star">
</p>
<p align="center">
  <a href="https://www.linkedin.com/company/nora-research-lab">LinkedIn</a> ·
  <a href="https://x.com/noraresearchlab">X / Twitter</a>
</p>

<p align="center">
  A unified API for satellite imagery, elevation, geophysics, and environmental data —<br>
  built so any of it can be pulled for AI training or geological analysis,<br>
  without hosting the underlying archives yourself.
</p>

<p align="center">
  <a href="https://agdfs.onrender.com">Live API</a> ·
  <a href="https://agdfs.onrender.com/docs">Interactive Docs</a> ·
  <a href="#-mcp--using-agdfs-as-an-ai-agent-tool">MCP for Agents</a> ·
  <a href="#-endpoint-reference">Endpoint Reference</a>
</p>

---

Built by NORA Research Lab as part of ongoing work at the intersection of geoscience, AI/ML, and remote sensing.

## Contents

- [Why AGDFS exists](#why-agdfs-exists)
- [Try it right now](#-try-it-right-now)
- [Endpoint reference](#-endpoint-reference)
- [How it works](#-how-it-works)
- [Data sources & attribution](#-data-sources--attribution)
- [MCP — using AGDFS as an AI agent tool](#-mcp--using-agdfs-as-an-ai-agent-tool)
- [Self-hosting](#-self-hosting)
- [Project structure](#-project-structure)
- [Known limitations](#-known-limitations)

---

## Why AGDFS exists

Geoscience AI work draws on many different data types — satellite imagery, elevation models, magnetic and gravity surveys — each hosted by a different provider, in a different format, with a different access pattern. Most of these datasets are enormous (some satellite archives run into petabytes; a single global gravity grid is hundreds of megabytes), which makes "just download everything" impractical for most people building AI tools on top of them.

AGDFS solves this with one consistent pattern across every endpoint: **query only the bounding box you need, fetched live from wherever the data actually lives.** Nothing is mirrored in bulk. The API is a thin, unified layer over sources that already do the heavy lifting — Microsoft's Planetary Computer, OpenTopography, NOAA, and the Bureau Gravimétrique International (BGI) — so you get one simple interface instead of four different ones.

## 🚀 Try it right now

The API is live at **`https://agdfs.onrender.com`** — no signup, no API key required to explore it.

> **Note:** this runs on Render's free tier, which sleeps after inactivity. The **first** request after idle time can take 30–50 seconds to wake up; every request after that is fast.

The fastest way to explore every endpoint interactively, with a "Try it out" button for each one, is the auto-generated docs:

👉 **[https://agdfs.onrender.com/docs](https://agdfs.onrender.com/docs)**

Or test straight from the command line:

```bash
# Satellite imagery over Lagos, Nigeria
curl "https://agdfs.onrender.com/imagery?lat=6.5244&lon=3.3792&date_from=2026-01-01&date_to=2026-07-01"

# Elevation over central Nigeria (requires a free OpenTopography key -- see below)
curl "https://agdfs.onrender.com/dem?lat=10&lon=9&buffer_deg=0.1&demtype=COP30"

# Magnetic anomaly
curl "https://agdfs.onrender.com/geophysics/magnetic?lat=9&lon=8&buffer_deg=0.5"

# Gravity anomaly (free-air or bouguer)
curl "https://agdfs.onrender.com/geophysics/gravity?lat=10&lon=8&buffer_deg=0.5&anomaly_type=freeair"
```

## 📡 Endpoint reference

### `GET /imagery` — Satellite imagery

Queries Sentinel-2 optical imagery via Microsoft's Planetary Computer STAC catalog.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `lat` | float | ✅ | Latitude of point of interest |
| `lon` | float | ✅ | Longitude of point of interest |
| `date_from` | string | ✅ | Start date, `YYYY-MM-DD` |
| `date_to` | string | ✅ | End date, `YYYY-MM-DD` |
| `buffer_deg` | float | – | Bounding box half-width in degrees (default `0.05`) |
| `limit` | int | – | Max number of scenes returned (default `5`, max `20`) |

**Example response:**
```json
{
  "count": 3,
  "results": [
    { "date": "2026-03-14T10:22:00Z", "cloud_cover": 4.2, "preview_url": "https://..." }
  ]
}
```

---

### `GET /dem` — Elevation data

Queries global elevation models via OpenTopography.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `lat` | float | ✅ | Latitude of point of interest |
| `lon` | float | ✅ | Longitude of point of interest |
| `buffer_deg` | float | – | Bounding box half-width in degrees (default `0.1`) |
| `demtype` | string | – | `SRTMGL1`, `SRTMGL3`, `COP30`, `NASADEM`, etc. (default `COP30`) |

**Requires** a free `OPENTOPO_API_KEY` set on the server (see [Self-hosting](#-self-hosting)). Get one instantly at [opentopography.org](https://opentopography.org).

---

### `GET /geophysics/magnetic` — Magnetic anomaly

Live-queries NOAA's EMAG2v3 global magnetic anomaly model. No caching, no API key required — this reads directly from NOAA's public ArcGIS ImageServer on every request.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `lat` | float | ✅ | Latitude of point of interest |
| `lon` | float | ✅ | Longitude of point of interest |
| `buffer_deg` | float | – | Bounding box half-width in degrees (default `0.5` — this grid is coarse, ~2 arcminutes, so a wider buffer than imagery/DEM is recommended) |

**Example response:**
```json
{
  "kind": "magnetic",
  "source": "NOAA EMAG2v3 (live query, no caching)",
  "bounds": { "south": 8.5, "north": 9.5, "west": 7.5, "east": 8.5 },
  "shape": [256, 256],
  "min": -15.3, "max": 40.7, "mean": 16.3,
  "values": [[...]]
}
```

---

### `GET /geophysics/gravity` — Gravity anomaly

Reads free-air or Bouguer gravity anomaly from WGM2012 (World Gravity Map 2012, published by BGI/CGMW/CNES/UNESCO), hosted as Cloud-Optimized GeoTIFFs and queried via HTTP range requests — only the bytes covering your bounding box are ever fetched, the full ~230MB grid is never downloaded.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `lat` | float | ✅ | Latitude of point of interest |
| `lon` | float | ✅ | Longitude of point of interest |
| `buffer_deg` | float | – | Bounding box half-width in degrees (default `0.5`) |
| `anomaly_type` | string | – | `freeair` or `bouguer` (default `freeair`) |

**Example response:**
```json
{
  "kind": "gravity_freeair",
  "source": "WGM2012 freeair anomaly (windowed read via HTTP range requests, no caching)",
  "bounds": { "south": 9.5, "north": 10.5, "west": 7.5, "east": 8.5 },
  "shape": [30, 30],
  "min": 1.9, "max": 69.6, "mean": 24.8,
  "values": [[...]]
}
```

---

### `GET /environment/soil` — Soil composition

Live query via ISRIC SoilGrids — clay, sand, silt %, pH, and organic carbon at 0-5cm depth.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `lat` / `lon` | float | ✅ | Point of interest |

---

### `GET /environment/weather` — Weather

Live query via Open-Meteo — current temperature, humidity, and rainfall.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `lat` / `lon` | float | ✅ | Point of interest |

---

### `GET /environment/earthquakes` — Seismic activity

Live query against USGS's global earthquake catalog.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `lat` / `lon` | float | ✅ | Point of interest |
| `buffer_deg` | float | – | Bounding box half-width in degrees (default `1.0`) |
| `days` | int | – | How many days back to search (default `30`) |
| `min_magnitude` | float | – | Minimum magnitude to include (default `2.5`) |

---

### `GET /environment/air-quality` — Air quality

Live query via Open-Meteo — current PM2.5, PM10, CO, NO₂, SO₂, ozone, and US AQI for a point.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `lat` / `lon` | float | ✅ | Point of interest |

## ⚙️ How it works

Every endpoint follows the same principle — **fetch only what's requested, store nothing permanently**:

- **Imagery & DEM** are proxied live to their source APIs (Planetary Computer, OpenTopography) — a direct pass-through, nothing cached.
- **Magnetic anomaly** is queried live from NOAA's own ArcGIS ImageServer, which supports bounding-box queries natively.
- **Gravity anomaly** has no equivalent live query service, so the source grids (from BGI) were converted once into Cloud-Optimized GeoTIFFs and hosted on Hugging Face. GDAL's HTTP range-request support (the same mechanism COGs are designed around) means only the relevant portion of that file is ever read — the server never downloads or stores the full grid.

This means AGDFS itself stays lightweight regardless of how large the underlying datasets are — there's no database, no persistent disk requirement, and no ongoing storage cost as usage grows.

## 🌍 Data sources & attribution

| Data | Source | Notes |
|---|---|---|
| Satellite imagery | [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/) | Sentinel-2 L2A, ESA Copernicus program |
| Elevation | [OpenTopography](https://opentopography.org/) | Multiple global DEMs (SRTM, Copernicus, NASADEM) |
| Magnetic anomaly | [NOAA NCEI](https://www.ncei.noaa.gov/) | EMAG2v3 |
| Gravity anomaly | [BGI — Bureau Gravimétrique International](https://bgi.obs-mip.fr/) | WGM2012 (Bonvalot et al., BGI/CGMW/CNES/UNESCO) |
| Earthquakes | [USGS](https://earthquake.usgs.gov/) | Live global earthquake catalog |
| Soil | [ISRIC SoilGrids](https://www.isric.org/) | 250m resolution, live query |
| Weather | [Open-Meteo](https://open-meteo.com/) | Live, no API key required |
| Air quality | [Open-Meteo](https://open-meteo.com/) | Live, no API key required |

Please review each provider's terms of use for your specific use case, particularly around attribution and rate limits.

## 🤖 MCP — using AGDFS as an AI agent tool

AGDFS exposes every endpoint above as an [MCP](https://modelcontextprotocol.io) tool as well as a plain REST API, using [`fastapi-mcp`](https://github.com/tadata-org/fastapi_mcp) — no separate implementation, the same code powers both.

**MCP endpoint:** `https://agdfs.onrender.com/mcp`

To connect an MCP-compatible client (Claude, or any other agent runtime), point it at that URL. Available tools:

- `get_satellite_imagery`
- `get_elevation`
- `get_magnetic_anomaly`
- `get_gravity_anomaly`
- `get_soil`
- `get_weather`
- `get_earthquakes`
- `get_air_quality`

For a plain-language guide written specifically for an AI agent consuming this API — covering units, sensible parameter ranges, and common pitfalls — see **[`AGENT.md`](./AGENT.md)**.

## 🛠 Self-hosting

<details>
<summary>Click to expand deployment instructions (Render)</summary>

1. Fork/clone this repo
2. On [Render](https://render.com): **New → Blueprint**, point it at your repo (reads `render.yaml` automatically)
3. Set environment variables in the Render dashboard:
   - `OPENTOPO_API_KEY` — required for `/dem`. Free, instant signup at [opentopography.org](https://opentopography.org)
   - `GRAVITY_FREEAIR_URL` / `GRAVITY_BOUGUER_URL` — optional, only needed if you're hosting your own copy of the gravity COGs instead of using the defaults
4. Deploy

See [`scripts/prepare_gravity_data.py`](./scripts/prepare_gravity_data.py) for how the gravity COGs were produced from the original BGI source grids, if you want to reproduce or update them.

</details>

## 📁 Project structure

```
agdfs/
├── main.py                       # FastAPI app -- all endpoints + MCP mount
├── geophysics.py                 # Magnetic (live query) + gravity (COG) logic
├── requirements.txt
├── render.yaml                   # Render Blueprint for one-command deploy
├── AGENT.md                      # API guide written for AI agents
├── README.md
└── scripts/
    └── prepare_gravity_data.py   # Reproducible pipeline: BGI source -> validated COG -> Hugging Face
```

## 📄 License

This project is licensed under the [MIT License](./LICENSE) — see the `LICENSE` file for the full text.

The AGDFS code is free to use, modify, and distribute. The underlying datasets accessed through the API remain governed by their original providers' own terms (see [Data sources & attribution](#-data-sources--attribution) above).

## ⚠️ Known limitations

- Free-tier hosting sleeps after inactivity -- expect a slow first request after idle periods.
- `/dem` requires an OpenTopography API key to function.
- Gravity data reflects WGM2012 (2012 release); it is not updated in real time.
- No authentication or rate limiting is currently implemented on the API itself -- deploy behind your own gateway if that matters for your use case.
