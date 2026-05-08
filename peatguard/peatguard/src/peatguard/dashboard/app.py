"""FastAPI dashboard application for PeatGuard COG product visualization.

Serves a Leaflet-based web map with TiTiler-powered dynamic tile endpoints
for each pipeline product stored in Google Cloud Storage.

Usage:
    uvicorn peatguard.dashboard.app:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from titiler.core.factory import TilerFactory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GCS_BUCKET = os.environ.get("PEATGUARD_STORAGE__GCS_BUCKET", "peatguard-data")
GCS_PREFIX = os.environ.get("PEATGUARD_GCS_PREFIX", "products")

# Public HTTPS URL pattern for COGs in GCS.  TiTiler reads COGs via HTTP
# range requests, so the bucket must either be public or accessed through
# signed URLs.  For simplicity we use the public storage.googleapis.com
# endpoint; swap to signed URLs if the bucket is private.
GCS_BASE_URL = f"https://storage.googleapis.com/{GCS_BUCKET}/{GCS_PREFIX}"

# AOI center (Teluk Bayur Village, West Kalimantan)
AOI_CENTER_LAT = -2.561
AOI_CENTER_LON = 114.354

# Product definitions: filename -> display metadata
PRODUCTS = {
    "subsidence_velocity.tif": {
        "label": "Subsidence Velocity (mm/yr)",
        "colormap": "rdbu_r",
        "rescale": "-60,20",
        "description": "InSAR-derived subsidence velocity. Blue = uplift, Red = subsidence.",
        "legend_type": "diverging",
        "legend_labels": ["-60 mm/yr (subsidence)", "0", "+20 mm/yr (uplift)"],
        "legend_colors": ["#d73027", "#ffffbf", "#4575b4"],
        "default_on": True,
    },
    "subsidence_class.tif": {
        "label": "Subsidence Classification",
        "colormap": "rdylgn_r",
        "rescale": "0,4",
        "description": "Severity classes: 1=Severe, 2=Active Drying, 3=Stable, 4=Uplift.",
        "legend_type": "categorical",
        "legend_labels": ["Severe", "Active Drying", "Stable", "Uplift"],
        "legend_colors": ["#d73027", "#fc8d59", "#91cf60", "#1a9850"],
        "default_on": False,
    },
    "canal_mask.tif": {
        "label": "Canal Network",
        "colormap": "blues",
        "rescale": "0,1",
        "description": "Detected drainage canals from VV backscatter.",
        "legend_type": "binary",
        "legend_labels": ["No Canal", "Canal"],
        "legend_colors": ["transparent", "#08519c"],
        "default_on": False,
    },
    "canal_risk.tif": {
        "label": "Canal Risk Score",
        "colormap": "rdylgn_r",
        "rescale": "0,1",
        "description": "Combined subsidence + canal proximity risk (0=low, 1=high).",
        "legend_type": "sequential",
        "legend_labels": ["0 (Low)", "0.5", "1.0 (High)"],
        "legend_colors": ["#1a9850", "#ffffbf", "#d73027"],
        "default_on": False,
    },
    "vv_median_db.tif": {
        "label": "VV Backscatter (dB)",
        "colormap": "greys",
        "rescale": "-25,-5",
        "description": "Median VV backscatter composite in decibels.",
        "legend_type": "sequential",
        "legend_labels": ["-25 dB", "-15 dB", "-5 dB"],
        "legend_colors": ["#000000", "#808080", "#ffffff"],
        "default_on": False,
    },
    "water_mask.tif": {
        "label": "Water Mask",
        "colormap": "blues",
        "rescale": "0,1",
        "description": "Water bodies detected from low VV backscatter.",
        "legend_type": "binary",
        "legend_labels": ["Land", "Water"],
        "legend_colors": ["transparent", "#2171b5"],
        "default_on": False,
    },
    "coherence_median.tif": {
        "label": "Temporal Coherence",
        "colormap": "viridis",
        "rescale": "0,1",
        "description": "Median InSAR coherence (0=decorrelated, 1=stable).",
        "legend_type": "sequential",
        "legend_labels": ["0 (Low)", "0.5", "1.0 (High)"],
        "legend_colors": ["#440154", "#21918c", "#fde725"],
        "default_on": False,
    },
}

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PeatGuard Dashboard",
    description="Web map viewer for PeatGuard COG products + operator/villager REST API",
    version="0.1.0",
)

# Permissive CORS for local dev (Next.js on :3000, Expo on exp://*).
# Tighten via PEATGUARD_API__CORS_ORIGINS for production.
_cors_origins = os.environ.get(
    "PEATGUARD_API__CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8081,http://localhost:19006,http://localhost:19000",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins + ["*"],  # "*" included so Expo Go on a phone can hit dev backend
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount TiTiler tile endpoints at /cog
cog_tiler = TilerFactory(router_prefix="/cog")
app.include_router(cog_tiler.router, prefix="/cog", tags=["COG Tiles"])

# Mount operator + villager REST API at /api/v1
from peatguard.api import api_router  # noqa: E402  (avoid circular import on dashboard.app)
from peatguard.api.db import init_db
from peatguard.api.seed import seed_if_empty

init_db()
seed_if_empty()
app.include_router(api_router, prefix="/api/v1")

# Jinja2 templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main dashboard page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": PRODUCTS,
            "gcs_base_url": GCS_BASE_URL,
            "center_lat": AOI_CENTER_LAT,
            "center_lon": AOI_CENTER_LON,
        },
    )


@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {"status": "ok"}


@app.get("/api/products")
async def list_products():
    """Return the list of available products and their tile URLs."""
    product_list = []
    for filename, meta in PRODUCTS.items():
        cog_url = f"{GCS_BASE_URL}/{filename}"
        tile_url = "/cog/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png"
        tile_url += f"?url={cog_url}"
        tile_url += f"&colormap_name={meta['colormap']}"
        tile_url += f"&rescale={meta['rescale']}"
        product_list.append(
            {
                "filename": filename,
                "label": meta["label"],
                "tile_url": tile_url,
                "cog_url": cog_url,
                "description": meta["description"],
                "legend_type": meta["legend_type"],
                "legend_labels": meta["legend_labels"],
                "legend_colors": meta["legend_colors"],
                "default_on": meta["default_on"],
            }
        )
    return {"products": product_list, "center": [AOI_CENTER_LAT, AOI_CENTER_LON]}
