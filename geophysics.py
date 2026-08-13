"""
geophysics.py

Handles global geophysics grids (magnetic anomaly, gravity anomaly).

Both are now served the same way: a live windowed read over HTTP, nothing
downloaded or cached on this server.

Magnetic (EMAG2v3): NOAA hosts this as a public ArcGIS ImageServer with a
bbox-queryable exportImage endpoint.

Gravity (WGM2012 free-air and Bouguer anomaly): no equivalent live query
service exists, so this reads pre-converted Cloud-Optimized GeoTIFFs
(COGs) hosted on Hugging Face instead. GDAL's https -> /vsicurl/ mapping
fetches only the byte ranges needed for the requested bounding box, via
the same HTTP range-request mechanism COGs are built for -- the full
~230MB file is never downloaded. See colab_wgm2012_final.py for how
those COGs were produced from the original BGI source grids.
"""

import io
import os
import requests
import rasterio
from rasterio.windows import from_bounds

MAGNETIC_EXPORT_URL = "https://gis.ngdc.noaa.gov/arcgis/rest/services/EMAG2v3/ImageServer/exportImage"


NATIVE_RES_DEG = 2 / 60  # EMAG2v3's real resolution, ~2 arcminutes


def clip_magnetic(south: float, north: float, west: float, east: float):
    """Query NOAA's live EMAG2v3 ImageServer directly for a bbox clip.

    Grid size is computed from the bbox relative to EMAG2v3's actual
    ~2 arcminute resolution, instead of a fixed 256x256 -- requesting
    more pixels than the source data actually has just returns
    interpolated filler, not real measurements. Nearest-neighbor (not
    bilinear) so returned values are the real source pixels, not
    blended/synthetic ones.

    NOAA's server occasionally responds slowly under load, so this retries
    once with a longer timeout before giving up.
    """
    width = max(2, min(256, round((east - west) / NATIVE_RES_DEG)))
    height = max(2, min(256, round((north - south) / NATIVE_RES_DEG)))

    params = {
        "bbox": f"{west},{south},{east},{north}",
        "bboxSR": 4326,
        "size": f"{width},{height}",
        "format": "tiff",
        "pixelType": "F32",
        "noData": "",
        "interpolation": "RSP_NearestNeighbor",
        "f": "image",
    }

    last_error = None
    for attempt, timeout in enumerate((30, 60), start=1):
        try:
            resp = requests.get(MAGNETIC_EXPORT_URL, params=params, timeout=timeout)
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            last_error = e
            if attempt == 2:
                raise
    else:
        raise last_error

    with rasterio.open(io.BytesIO(resp.content)) as src:
        data = src.read(1)

    return {
        "kind": "magnetic",
        "source": "NOAA EMAG2v3 (live query, no caching)",
        "bounds": {"south": south, "north": north, "west": west, "east": east},
        "shape": data.shape,
        "min": float(data.min()) if data.size else None,
        "max": float(data.max()) if data.size else None,
        "mean": float(data.mean()) if data.size else None,
        "values": data.tolist(),
    }


GRAVITY_COG_URLS = {
    "freeair": os.environ.get(
        "GRAVITY_FREEAIR_URL",
        "https://huggingface.co/datasets/Adedoyinjames/AGDFS-DATA/resolve/main/wgm2012_freeair_cog.tif",
    ),
    "bouguer": os.environ.get(
        "GRAVITY_BOUGUER_URL",
        "https://huggingface.co/datasets/Adedoyinjames/AGDFS-DATA/resolve/main/wgm2012_bouguer_cog.tif",
    ),
}


def clip_gravity(south: float, north: float, west: float, east: float, anomaly_type: str = "freeair"):
    """
    Read a bbox window directly from the WGM2012 gravity COG (free-air or
    Bouguer, real WGM2012 data from BGI, validated for real spatial
    variation and correct georeferencing). Uses rasterio's built-in
    https -> /vsicurl/ mapping, so only the byte ranges covering the
    requested window are fetched -- the full ~230MB file is never
    downloaded, and nothing is stored on this server.
    """
    if anomaly_type not in GRAVITY_COG_URLS:
        raise ValueError(f"anomaly_type must be one of {list(GRAVITY_COG_URLS)}, got '{anomaly_type}'")

    url = GRAVITY_COG_URLS[anomaly_type]

    with rasterio.open(url) as src:
        window = from_bounds(west, south, east, north, transform=src.transform)
        data = src.read(1, window=window)

    return {
        "kind": f"gravity_{anomaly_type}",
        "source": f"WGM2012 {anomaly_type} anomaly (windowed read via HTTP range requests, no caching)",
        "bounds": {"south": south, "north": north, "west": west, "east": east},
        "shape": data.shape,
        "min": float(data.min()) if data.size else None,
        "max": float(data.max()) if data.size else None,
        "mean": float(data.mean()) if data.size else None,
        "values": data.tolist(),
    }
    
