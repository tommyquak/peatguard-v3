"""Pipeline configuration management.

Loads settings from YAML config files with environment variable overrides.
All pipeline parameters are centralized here to eliminate hardcoded values
scattered across processing scripts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class AOIConfig(BaseModel):
    """Area of interest definition."""

    bbox: list[float] = Field(
        description="Bounding box as [west, south, east, north] in geographic coordinates"
    )
    epsg: int = Field(default=32649, description="Target CRS EPSG code")

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: list[float]) -> list[float]:
        if len(v) != 4:
            raise ValueError("bbox must have exactly 4 values: [west, south, east, north]")
        west, south, east, north = v
        if west >= east:
            raise ValueError(f"west ({west}) must be less than east ({east})")
        if south >= north:
            raise ValueError(f"south ({south}) must be less than north ({north})")
        return v


class Sentinel1Config(BaseModel):
    """Sentinel-1 acquisition parameters."""

    platform: str = "SENTINEL-1"
    polarization: str = "VV"
    subswath: str = "IW3"
    processing_level_slc: str = "SLC"
    processing_level_grd: str = "GRD_HD"
    beam_mode: str = "IW"
    min_temporal_gap_days: int = 14
    max_temporal_baseline_days: int = 48


class NISARConfig(BaseModel):
    """NISAR L-band acquisition parameters.

    NISAR uses L-band (24cm wavelength) which penetrates tropical forest
    canopy, enabling subsidence measurement under intact peat forest where
    C-band Sentinel-1 loses coherence.

    Data is freely available from ASF DAAC since February 2026.
    """

    platform: str = "NISAR"
    polarization: str = "HH"
    beam_mode: str = "ALOS"  # NISAR L-SAR uses ALOS-compatible beam mode designation
    processing_level: str = "SLC"
    min_temporal_gap_days: int = 12  # NISAR repeat cycle is 12 days
    max_temporal_baseline_days: int = 48
    wavelength_m: float = 0.2384  # L-band, 24cm
    orbit_height_m: float = 747000.0  # ~747 km orbit altitude
    range_pixel_size_m: float = 7.5  # approximate, varies by mode
    azimuth_pixel_size_m: float = 6.0  # approximate, varies by mode
    incidence_deg: float = 33.9  # typical mid-swath incidence angle


class ProcessingConfig(BaseModel):
    """InSAR and backscatter processing parameters."""

    resolution_m: float = 10.0
    coherence_threshold: float = 0.3
    wavelength_m: float = 0.056
    incidence_deg: float = 37.0
    dem_source: str = "SRTM"
    speckle_filter: str = "lee_sigma"
    speckle_window_size: int = 7
    goldstein_alpha: float = 0.8
    snaphu_cost_mode: str = "DEFO"
    do_ion: bool = True  # Ionospheric correction via split-spectrum (recommended for equatorial)


class ClassificationConfig(BaseModel):
    """Subsidence classification thresholds in mm/yr.

    Natural peat accumulation is ~1 mm/yr. Any subsidence below
    -5 mm/yr on peat indicates net carbon loss, so "stable" is
    restricted to the +/-5 mm/yr natural variability envelope.
    """

    severe_threshold: float = -50.0
    active_drying_threshold: float = -20.0
    moderate_drying_threshold: float = -5.0
    stable_threshold: float = 5.0


class WaterMaskConfig(BaseModel):
    """Water body detection parameters.

    Controls VV backscatter-based water masking to prevent false
    subsidence detections over water bodies. Water shows specular
    reflection (very low backscatter) that can mimic low coherence.
    """

    enabled: bool = True
    vv_threshold_db: float = Field(
        default=-20.0,
        description=(
            "VV backscatter threshold in dB. Pixels below this are water. "
            "-20 dB is conservative for tropical peatlands."
        ),
    )
    min_water_size_pixels: int = Field(
        default=50,
        description=(
            "Minimum connected component size (pixels) to retain as water. "
            "At 10m resolution, 50 pixels = 5000 sq m (small pond)."
        ),
    )
    closing_radius: int = Field(
        default=3,
        description="Morphological closing radius to fill gaps in water bodies.",
    )
    exclude_canals: bool = Field(
        default=True,
        description=(
            "Remove canal pixels from water mask to avoid interfering "
            "with canal_detect.py results."
        ),
    )


class PeatMaskConfig(BaseModel):
    """Peat extent mapping and masking parameters.

    Downloads peat polygons from the WRI/GFW Indonesia Peatlands dataset
    and rasterizes them to produce peat-masked subsidence products.
    Peat depth is estimated from distance-to-edge using the tropical
    peatland dome model (Page et al., 2006).
    """

    enabled: bool = Field(
        default=True,
        description="Enable peat extent mapping and masking.",
    )
    shallow_edge_m: float = Field(
        default=500.0,
        description=(
            "Distance from peat edge for shallow peat classification (meters). "
            "Pixels within this distance of the peat boundary are classified shallow."
        ),
    )
    moderate_edge_m: float = Field(
        default=1500.0,
        description=(
            "Distance from peat edge for moderate peat classification (meters). "
            "Pixels between shallow_edge_m and this distance are moderate; "
            "beyond this distance are classified as deep peat."
        ),
    )


class RiskScoreConfig(BaseModel):
    """Risk score parameters calibrated to Hooijer et al. (2012).

    Proximity decay uses a linear model based on the Dupuit equation
    approximation: water table drawdown is roughly linear with distance
    from drainage canals in tropical peat, with effects extending 1-1.5 km.
    """

    proximity_weight: float = Field(
        default=0.45,
        description="Weight for canal proximity component (indirect proxy).",
    )
    subsidence_weight: float = Field(
        default=0.55,
        description="Weight for subsidence velocity component (direct measurement).",
    )
    max_influence_m: float = Field(
        default=1200.0,
        description=(
            "Canal influence radius in meters. Hooijer et al. (2012) and "
            "Jaenicke et al. (2010) found drainage effects extend 1-1.5 km."
        ),
    )
    severe_velocity_mm_yr: float = Field(
        default=-40.0,
        description=(
            "Velocity at which subsidence risk saturates (mm/yr). "
            "Hooijer (2012): 20-50 mm/yr in first 5 years of drainage."
        ),
    )


class FusionConfig(BaseModel):
    """Multi-sensor fusion parameters for combining C-band and L-band velocity.

    Fusion is only performed when both Sentinel-1 (C-band) and NISAR
    (L-band) velocity products are available. The coherence-weighted
    averaging strategy naturally favors the sensor with better signal
    quality at each pixel.
    """

    enabled: bool = Field(
        default=False,
        description=(
            "Enable multi-sensor fusion. Only takes effect when both "
            "C-band and L-band velocity products exist."
        ),
    )
    c_band_weight_boost: float = Field(
        default=1.0,
        description=(
            "Multiplicative boost for C-band coherence weight in dual-coverage "
            "areas. 1.0 = pure coherence weighting. Values > 1.0 increase "
            "C-band influence, which may be desirable because C-band has "
            "higher deformation sensitivity (shorter wavelength) over cleared land."
        ),
    )
    min_coherence: float = Field(
        default=0.3,
        description=(
            "Minimum temporal coherence for a sensor to contribute to the "
            "fused velocity. Pixels below this threshold are treated as "
            "invalid for that sensor. Matches the pipeline coherence_threshold."
        ),
    )


class ValidationConfig(BaseModel):
    """Cross-validation settings for independent verification of InSAR velocity.

    Computes spatial correlations between subsidence velocity and
    independent datasets (backscatter, coherence, canal distance, NDVI)
    to provide evidence that the InSAR signal reflects real ground motion.
    """

    enabled: bool = Field(
        default=True,
        description="Enable cross-validation after analysis stage.",
    )
    attempt_ndvi_download: bool = Field(
        default=True,
        description=(
            "Attempt to download Sentinel-2 NDVI composite from Planetary Computer. "
            "Requires pystac-client and planetary-computer packages. If unavailable, "
            "validation proceeds with SAR-only products."
        ),
    )
    ndvi_max_cloud_cover: int = Field(
        default=30,
        description="Maximum cloud cover percentage for Sentinel-2 scene selection.",
    )
    ndvi_max_scenes: int = Field(
        default=20,
        description="Maximum number of Sentinel-2 scenes for the NDVI composite.",
    )
    coherence_threshold: float = Field(
        default=0.5,
        description=(
            "Coherence threshold for zonal analysis. Pixels above this "
            "are classified as 'cleared'; below as 'forested'."
        ),
    )


class ExportConfig(BaseModel):
    """Output format settings for ArcGIS Pro compatibility."""

    cog_blocksize: int = 512
    cog_compression: str = "DEFLATE"
    overview_levels: list[int] = Field(default=[2, 4, 8, 16])
    nodata: float = -9999.0


class StorageConfig(BaseModel):
    """Local and cloud storage paths."""

    output_dir: Path = Path("./output")
    scratch_dir: Path = Path("./scratch")
    catalog_db: Path = Path("./catalog.db")
    gcs_bucket: str = ""
    gcs_prefix: str = "peatguard-data"

    @field_validator("output_dir", "scratch_dir", "catalog_db", mode="after")
    @classmethod
    def resolve_paths(cls, v: Path) -> Path:
        """Ensure all paths are absolute to avoid cwd-relative issues."""
        return v.resolve()


class MintPyNetworkConfig(BaseModel):
    """MintPy network modification settings."""

    coherence_based: bool = True
    min_coherence: float = 0.3


class MintPyConfig(BaseModel):
    """MintPy time-series processing settings."""

    reference_lalo: list[float] = Field(
        default=[-2.496900, 114.312148],
        description=(
            "Fixed reference point as [lat, lon] for velocity baseline. "
            "Set to empty list [] to fall back to MintPy auto-selection."
        ),
    )
    reference_min_coherence: float = Field(
        default=0.7,
        description="Minimum coherence for reference point (auto-select fallback).",
    )
    tropospheric_correction: str = "pyaps"
    unwrap_error_correction: str = "bridging+phase_closure"
    network_modification: MintPyNetworkConfig = Field(default_factory=MintPyNetworkConfig)

    @field_validator("reference_lalo")
    @classmethod
    def validate_reference_lalo(cls, v: list[float]) -> list[float]:
        if len(v) == 0:
            return v
        if len(v) != 2:
            raise ValueError("reference_lalo must be [lat, lon] (2 values) or [] for auto")
        lat, lon = v
        if not (-90 <= lat <= 90):
            raise ValueError(f"reference latitude {lat} out of range [-90, 90]")
        if not (-180 <= lon <= 180):
            raise ValueError(f"reference longitude {lon} out of range [-180, 180]")
        return v


class PeatGuardConfig(BaseModel):
    """Root configuration for the PeatGuard pipeline."""

    sensor: Literal["sentinel1", "nisar"] = Field(
        default="sentinel1",
        description=(
            "Active sensor selection. 'sentinel1' uses C-band TOPS mode "
            "(topsApp). 'nisar' uses L-band stripmap mode (stripmapApp)."
        ),
    )
    aoi: AOIConfig
    sentinel1: Sentinel1Config = Field(default_factory=Sentinel1Config)
    nisar: NISARConfig = Field(default_factory=NISARConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    water_mask: WaterMaskConfig = Field(default_factory=WaterMaskConfig)
    peat_mask: PeatMaskConfig = Field(default_factory=PeatMaskConfig)
    risk_score: RiskScoreConfig = Field(default_factory=RiskScoreConfig)
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    mintpy: MintPyConfig = Field(default_factory=MintPyConfig)

    @property
    def is_nisar(self) -> bool:
        """Return True if the active sensor is NISAR."""
        return self.sensor == "nisar"

    @property
    def active_sensor_config(self) -> Sentinel1Config | NISARConfig:
        """Return the config object for the active sensor."""
        return self.nisar if self.is_nisar else self.sentinel1


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override dict into base dict."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_env_overrides(data: dict) -> dict:
    """Apply environment variable overrides.

    Environment variables use double underscore as the section separator:
        PEATGUARD_<SECTION>__<KEY>=value

    For example: PEATGUARD_STORAGE__GCS_BUCKET=my-bucket
    Single underscores within section or key names are preserved.
    """
    env_prefix = "PEATGUARD_"
    for env_key, env_value in os.environ.items():
        if not env_key.startswith(env_prefix):
            continue
        remainder = env_key[len(env_prefix):]
        if "__" not in remainder:
            continue
        section, key = remainder.split("__", 1)
        section = section.lower()
        key = key.lower()
        if section in data and isinstance(data[section], dict):
            data[section][key] = env_value
    return data


def load_config(
    config_path: Optional[Path] = None,
    override_path: Optional[Path] = None,
) -> PeatGuardConfig:
    """Load pipeline configuration from YAML files.

    Args:
        config_path: Path to the base config YAML. Defaults to config/default.yaml
            relative to the package root.
        override_path: Optional path to an override YAML that is merged on top
            of the base config.

    Returns:
        Validated PeatGuardConfig instance.
    """
    if config_path is None:
        # Look for bundled config inside the package first, then fall back to source tree
        pkg_config = Path(__file__).parent / "data" / "default.yaml"
        src_config = Path(__file__).parent.parent.parent / "config" / "default.yaml"
        config_path = pkg_config if pkg_config.exists() else src_config

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if override_path is not None:
        with open(override_path) as f:
            override_data = yaml.safe_load(f)
        if override_data:
            data = _deep_merge(data, override_data)

    data = _apply_env_overrides(data)
    return PeatGuardConfig(**data)
