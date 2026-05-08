"""Re-export the existing TiTiler product catalog as JSON.

The map deep-dive screen (W3) builds tile URLs against ``/cog/...``; this
endpoint hands it the metadata (filename, colormap, rescale, legend) so the
client doesn't duplicate the dictionary that already lives in
``dashboard/app.py``.
"""

from __future__ import annotations

from fastapi import APIRouter

from peatguard.dashboard.app import GCS_BASE_URL, PRODUCTS

router = APIRouter()


@router.get("/products")
def list_products() -> dict:
    items = []
    for filename, meta in PRODUCTS.items():
        cog_url = f"{GCS_BASE_URL}/{filename}"
        tile_url = (
            "/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png"
            f"?url={cog_url}&colormap_name={meta['colormap']}&rescale={meta['rescale']}"
        )
        items.append(
            {
                "id": filename.replace(".tif", ""),
                "filename": filename,
                "label": meta["label"],
                "description": meta["description"],
                "tile_url": tile_url,
                "cog_url": cog_url,
                "colormap": meta["colormap"],
                "rescale": meta["rescale"],
                "legend_type": meta["legend_type"],
                "legend_labels": meta["legend_labels"],
                "legend_colors": meta["legend_colors"],
                "default_on": meta["default_on"],
            }
        )
    return {"products": items}
