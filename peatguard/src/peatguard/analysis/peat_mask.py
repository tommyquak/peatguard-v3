"""Peat extent mapping from the WRI/GFW Indonesia Peatlands dataset.

Downloads peat polygons from the WRI Global Forest Watch ArcGIS MapServer,
rasterizes them to match the pipeline's raster grid, and produces peat-masked
subsidence products. This allows distinguishing peatland subsidence (the
primary target for restoration) from non-peat subsidence.

Data source:
    WRI/GFW Indonesia Peat Lands (derived from Wetlands International / CIFOR)
    MapServer: gis-gfw.wri.org/arcgis/rest/services/country_data/asia/MapServer/10
    Geometry: polygons, EPSG:3857 (Web Mercator)
    Coverage: Indonesia and parts of Malaysia
    License: Open data, free for non-commercial use

The dataset provides peat extent polygons but no depth attribute. Peat depth
is estimated from distance-to-edge using the dome model common in tropical
peatlands: deeper peat tends to occur further from the margins (Page et al.,
2006; Jaenicke et al., 2008).
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.parse
from pathlib import Path

import numpy as np

from peatguard.export.cog import read_raster, write_cog

logger = logging.getLogger(__name__)

# WRI/GFW Indonesia Peat Lands MapServer layer
_GFW_PEAT_MAPSERVER = (
    "https://gis-gfw.wri.org/arcgis/rest/services/"
    "country_data/asia/MapServer/10"
)

# Peat depth classes (uint8)
PEAT_NODATA = 255
PEAT_NONE = 0       # Not peatland
PEAT_SHALLOW = 1    # Estimated < 2m depth (edge zone)
PEAT_MODERATE = 2   # Estimated 2-4m depth (intermediate)
PEAT_DEEP = 3       # Estimated > 4m depth (dome interior)

PEAT_DEPTH_LABELS = {
    PEAT_NODATA: "NoData",
    PEAT_NONE: "Non-peat",
    PEAT_SHALLOW: "Shallow peat (< 2m est.)",
    PEAT_MODERATE: "Moderate peat (2-4m est.)",
    PEAT_DEEP: "Deep peat (> 4m est.)",
}

# Distance-to-edge thresholds for depth estimation (meters).
# Based on Page et al. (2006) dome model for Kalimantan peatlands:
# shallow peat at margins, deepening toward interior.
_SHALLOW_EDGE_M = 500.0   # < 500m from edge -> shallow
_MODERATE_EDGE_M = 1500.0  # 500-1500m from edge -> moderate
# > 1500m from edge -> deep


def download_peat_polygons(
    bbox: list[float],
    output_path: Path,
    mapserver_url: str = _GFW_PEAT_MAPSERVER,
) -> Path:
    """Download peat extent polygons from the WRI/GFW ArcGIS MapServer.

    Queries the MapServer for features intersecting the bounding box and
    saves the result as GeoJSON.

    Args:
        bbox: Bounding box as [west, south, east, north] in EPSG:4326.
        output_path: Path to save the GeoJSON file.
        mapserver_url: ArcGIS MapServer layer URL.

    Returns:
        Path to the downloaded GeoJSON file.

    Raises:
        RuntimeError: If the download fails after retries.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    west, south, east, north = bbox
    # ArcGIS geometry envelope format, in EPSG:4326
    geometry_envelope = f"{west},{south},{east},{north}"

    params = {
        "where": "1=1",
        "geometry": geometry_envelope,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "outSR": "4326",
        "f": "geojson",
    }

    query_url = f"{mapserver_url}/query?{urllib.parse.urlencode(params)}"
    logger.info("Downloading peat polygons from WRI/GFW MapServer")
    logger.info("Query URL: %s", query_url)

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(
                query_url,
                headers={"User-Agent": "PeatGuard/1.0"},
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                data = response.read()
                geojson = json.loads(data)

            if "features" not in geojson:
                raise RuntimeError(
                    f"Unexpected response from MapServer: {list(geojson.keys())}"
                )

            n_features = len(geojson["features"])
            logger.info(
                "Downloaded %d peat polygon(s) for bbox %s",
                n_features, bbox,
            )

            with open(output_path, "w") as f:
                json.dump(geojson, f)

            return output_path

        except Exception as exc:
            logger.warning(
                "Download attempt %d/%d failed: %s", attempt, max_retries, exc
            )
            if attempt == max_retries:
                raise RuntimeError(
                    f"Failed to download peat polygons after {max_retries} attempts: {exc}"
                ) from exc

    # Unreachable, but satisfies type checker
    raise RuntimeError("Download failed")


def _create_fallback_peat_geojson(
    bbox: list[float],
    output_path: Path,
) -> Path:
    """Create a fallback GeoJSON covering the entire AOI as peatland.

    Used when the WRI/GFW download fails. This is a reasonable assumption
    for the Kapuas River region in West Kalimantan, which is predominantly
    peatland (Hooijer et al., 2010).

    Args:
        bbox: Bounding box as [west, south, east, north] in EPSG:4326.
        output_path: Path to save the fallback GeoJSON.

    Returns:
        Path to the fallback GeoJSON.
    """
    west, south, east, north = bbox
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"source": "fallback_full_aoi"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [west, south],
                            [east, south],
                            [east, north],
                            [west, north],
                            [west, south],
                        ]
                    ],
                },
            }
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(geojson, f)

    logger.warning(
        "Using fallback peat extent: entire AOI assumed peatland. "
        "This is reasonable for the Kapuas region but should be replaced "
        "with actual peat map data when available."
    )
    return output_path


def rasterize_peat_extent(
    vector_path: Path,
    reference_raster_path: Path,
    output_path: Path,
) -> Path:
    """Rasterize peat polygons to a binary mask matching the reference grid.

    Burns peat polygons into a raster aligned with the reference raster's
    CRS, extent, and resolution. Result: 1 = peat, 0 = non-peat.

    Args:
        vector_path: Path to peat polygons (GeoJSON or Shapefile).
        reference_raster_path: Path to a reference raster for grid alignment.
        output_path: Path for the output raster.

    Returns:
        Path to the binary peat extent raster (uint8).
    """
    import rasterio
    from rasterio.features import rasterize
    import fiona
    from shapely.geometry import shape
    from shapely.ops import transform as shapely_transform
    import pyproj

    _, ref_meta = read_raster(reference_raster_path)
    ref_crs = ref_meta["crs"]
    ref_transform = ref_meta["transform"]
    ref_height = ref_meta["height"]
    ref_width = ref_meta["width"]

    # Read vector features and reproject to reference CRS
    geometries = []
    with fiona.open(vector_path) as src:
        src_crs = src.crs
        # Set up reprojection if needed
        if src_crs and str(src_crs) != str(ref_crs):
            transformer = pyproj.Transformer.from_crs(
                pyproj.CRS(src_crs),
                pyproj.CRS(ref_crs),
                always_xy=True,
            )
            project_fn = transformer.transform
        else:
            project_fn = None

        for feature in src:
            geom = shape(feature["geometry"])
            if project_fn is not None:
                geom = shapely_transform(project_fn, geom)
            if not geom.is_empty:
                geometries.append((geom, 1))

    if not geometries:
        logger.warning("No peat polygons found in %s, creating empty mask", vector_path)
        peat_raster = np.zeros((ref_height, ref_width), dtype=np.uint8)
    else:
        logger.info("Rasterizing %d peat polygon(s) to %dx%d grid", len(geometries), ref_width, ref_height)
        peat_raster = rasterize(
            geometries,
            out_shape=(ref_height, ref_width),
            transform=ref_transform,
            fill=0,
            dtype=np.uint8,
        )

    n_peat = (peat_raster == 1).sum()
    n_total = peat_raster.size
    logger.info(
        "Peat extent: %d/%d pixels (%.1f%%) classified as peatland",
        n_peat, n_total, n_peat / max(1, n_total) * 100,
    )

    output_path = Path(output_path)
    return write_cog(
        data=peat_raster,
        output_path=output_path,
        crs=ref_crs,
        transform=ref_transform,
        nodata=PEAT_NODATA,
        band_names=["peat_extent"],
        dtype="uint8",
    )


def classify_peat_depth(
    peat_binary_path: Path,
    output_path: Path,
    shallow_edge_m: float = _SHALLOW_EDGE_M,
    moderate_edge_m: float = _MODERATE_EDGE_M,
) -> Path:
    """Estimate peat depth classes from distance to peat edge.

    Uses the dome model (Page et al., 2006): tropical peatlands form
    raised domes where depth increases with distance from the edge.
    The distance-to-edge is computed from the binary peat mask using
    the Euclidean distance transform.

    Args:
        peat_binary_path: Path to binary peat mask (1=peat, 0=non-peat).
        output_path: Path for classified peat depth raster.
        shallow_edge_m: Distance threshold for shallow peat (meters).
        moderate_edge_m: Distance threshold for moderate peat (meters).

    Returns:
        Path to peat depth classification raster (uint8: 0-3).
    """
    from scipy.ndimage import distance_transform_edt

    data, meta = read_raster(peat_binary_path)
    peat_binary = data[0]

    # Compute pixel size in meters from the transform
    # For projected CRS (UTM), pixel size is directly in meters.
    # For geographic CRS, approximate using latitude.
    transform = meta["transform"]
    pixel_x = abs(transform.a)
    pixel_y = abs(transform.e)

    crs = meta["crs"]
    crs_str = str(crs) if crs else ""
    if "4326" in crs_str or "epsg:4326" in crs_str.lower():
        # Approximate meters per degree at the AOI latitude
        center_y = transform.f + (meta["height"] / 2) * transform.e
        m_per_deg_lat = 111320.0
        m_per_deg_lon = 111320.0 * np.cos(np.radians(abs(center_y)))
        pixel_x_m = pixel_x * m_per_deg_lon
        pixel_y_m = pixel_y * m_per_deg_lat
    else:
        pixel_x_m = pixel_x
        pixel_y_m = pixel_y

    logger.info(
        "Pixel size for distance transform: %.1f x %.1f m",
        pixel_x_m, pixel_y_m,
    )

    # Distance from non-peat edge into peat interior (in pixels)
    # Invert: distance_transform_edt computes distance from 0-pixels
    peat_mask = peat_binary > 0
    if not peat_mask.any():
        logger.warning("No peat pixels found, creating empty depth classification")
        depth_class = np.zeros_like(peat_binary, dtype=np.uint8)
    else:
        # Distance from the peat boundary into the interior
        dist_pixels = distance_transform_edt(peat_mask, sampling=[pixel_y_m, pixel_x_m])

        depth_class = np.full_like(peat_binary, PEAT_NONE, dtype=np.uint8)
        depth_class[peat_mask & (dist_pixels <= shallow_edge_m)] = PEAT_SHALLOW
        depth_class[
            peat_mask
            & (dist_pixels > shallow_edge_m)
            & (dist_pixels <= moderate_edge_m)
        ] = PEAT_MODERATE
        depth_class[peat_mask & (dist_pixels > moderate_edge_m)] = PEAT_DEEP

    # Log distribution
    for code, label in PEAT_DEPTH_LABELS.items():
        if code == PEAT_NODATA:
            continue
        count = (depth_class == code).sum()
        pct = count / depth_class.size * 100
        logger.info("  %s: %d pixels (%.1f%%)", label, count, pct)

    return write_cog(
        data=depth_class,
        output_path=output_path,
        crs=meta["crs"],
        transform=meta["transform"],
        nodata=PEAT_NODATA,
        band_names=["peat_depth_class"],
        dtype="uint8",
    )


def apply_peat_mask(
    subsidence_raster_path: Path,
    peat_binary_path: Path,
    output_path: Path,
) -> Path:
    """Mask subsidence to peat areas only.

    Pixels outside peat extent are set to nodata. This produces a
    peat-only subsidence product for focused analysis.

    Args:
        subsidence_raster_path: Path to subsidence velocity GeoTIFF (mm/yr).
        peat_binary_path: Path to binary peat mask (1=peat, 0=non-peat).
        output_path: Path for masked output.

    Returns:
        Path to the peat-masked subsidence GeoTIFF.
    """
    from rasterio.warp import Resampling, reproject

    vel_data, vel_meta = read_raster(subsidence_raster_path)
    velocity = vel_data[0]
    vel_nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0

    peat_data, peat_meta = read_raster(peat_binary_path)
    peat = peat_data[0]

    # Handle shape/CRS mismatch by reprojecting peat mask to velocity grid
    if peat.shape != velocity.shape:
        logger.info(
            "Reprojecting peat mask from %s to velocity grid %s",
            peat.shape, velocity.shape,
        )
        peat_reprojected = np.zeros(velocity.shape, dtype=np.uint8)
        reproject(
            source=peat.astype(np.uint8),
            destination=peat_reprojected,
            src_transform=peat_meta["transform"],
            src_crs=peat_meta["crs"],
            dst_transform=vel_meta["transform"],
            dst_crs=vel_meta["crs"],
            resampling=Resampling.nearest,
        )
        peat = peat_reprojected

    # Mask: set non-peat pixels to nodata
    masked = velocity.copy()
    non_peat = peat == 0
    masked[non_peat] = vel_nodata

    n_peat_pixels = (peat > 0).sum()
    n_valid_vel = ((velocity != vel_nodata) & np.isfinite(velocity)).sum()
    n_masked_out = (non_peat & (velocity != vel_nodata) & np.isfinite(velocity)).sum()
    logger.info(
        "Peat mask applied: %d valid velocity pixels, %d on peat, %d masked out",
        n_valid_vel, n_valid_vel - n_masked_out, n_masked_out,
    )

    return write_cog(
        data=masked,
        output_path=output_path,
        crs=vel_meta["crs"],
        transform=vel_meta["transform"],
        nodata=vel_nodata,
        band_names=["peat_subsidence_velocity"],
        dtype="float32",
    )


def compute_peat_risk_weight(
    peat_depth_path: Path,
) -> np.ndarray:
    """Compute peat depth weighting for risk score enhancement.

    Deeper peat has higher carbon stocks and greater irreversibility of
    degradation, so deeper peat areas receive higher risk priority.

    Returns a multiplicative weight array:
        - Non-peat: 0.0 (excluded from peat risk)
        - Shallow: 0.6
        - Moderate: 0.8
        - Deep: 1.0

    Args:
        peat_depth_path: Path to peat depth classification raster.

    Returns:
        2D float32 array of peat depth weights (0.0-1.0).
    """
    data, _ = read_raster(peat_depth_path)
    depth_class = data[0]

    weights = np.zeros(depth_class.shape, dtype=np.float32)
    weights[depth_class == PEAT_SHALLOW] = 0.6
    weights[depth_class == PEAT_MODERATE] = 0.8
    weights[depth_class == PEAT_DEEP] = 1.0

    logger.info(
        "Peat depth weights: mean=%.3f (peat pixels only), coverage=%.1f%%",
        weights[weights > 0].mean() if (weights > 0).any() else 0.0,
        (weights > 0).sum() / max(1, weights.size) * 100,
    )

    return weights


def generate_peat_products(
    bbox: list[float],
    reference_raster_path: Path,
    velocity_path: Path,
    output_dir: Path,
    shallow_edge_m: float = _SHALLOW_EDGE_M,
    moderate_edge_m: float = _MODERATE_EDGE_M,
) -> dict[str, Path]:
    """Generate all peat-related products for the analysis pipeline.

    This is the main entry point called from the orchestrator. It:
    1. Downloads (or creates fallback) peat polygons
    2. Rasterizes to match the pipeline grid
    3. Classifies estimated peat depth
    4. Creates peat-masked subsidence product

    Args:
        bbox: AOI bounding box [west, south, east, north] in EPSG:4326.
        reference_raster_path: Path to a reference raster for grid alignment
            (typically the velocity or backscatter product).
        velocity_path: Path to subsidence velocity GeoTIFF (mm/yr).
        output_dir: Directory for output products.
        shallow_edge_m: Distance-to-edge threshold for shallow peat (meters).
        moderate_edge_m: Distance-to-edge threshold for moderate peat (meters).

    Returns:
        Dict mapping product names to output file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    products = {}

    # Step 1: Download peat polygons
    geojson_path = output_dir / "peat_polygons.geojson"
    try:
        download_peat_polygons(bbox, geojson_path)
        # Check if any features were returned
        with open(geojson_path) as f:
            geojson = json.load(f)
        if not geojson.get("features"):
            logger.warning("No peat features returned for AOI, using fallback")
            _create_fallback_peat_geojson(bbox, geojson_path)
    except Exception as exc:
        logger.warning("Peat map download failed: %s. Using fallback.", exc)
        _create_fallback_peat_geojson(bbox, geojson_path)

    # Step 2: Rasterize to binary peat mask
    peat_binary_path = output_dir / "peat_extent_binary.tif"
    rasterize_peat_extent(geojson_path, reference_raster_path, peat_binary_path)
    products["peat_extent_binary"] = peat_binary_path

    # Step 3: Classify peat depth
    peat_depth_path = output_dir / "peat_extent.tif"
    classify_peat_depth(
        peat_binary_path, peat_depth_path,
        shallow_edge_m=shallow_edge_m,
        moderate_edge_m=moderate_edge_m,
    )
    products["peat_extent"] = peat_depth_path

    # Step 4: Create peat-masked subsidence
    peat_subsidence_path = output_dir / "peat_subsidence.tif"
    apply_peat_mask(velocity_path, peat_binary_path, peat_subsidence_path)
    products["peat_subsidence"] = peat_subsidence_path

    logger.info("Peat products generated: %s", list(products.keys()))
    return products
