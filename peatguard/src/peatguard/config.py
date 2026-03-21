"""Pipeline configuration management.

Loads settings from YAML config files with environment variable overrides.
All pipeline parameters are centralized here to eliminate hardcoded values
scattered across processing scripts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

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


class ClassificationConfig(BaseModel):
    """Subsidence classification thresholds in mm/yr."""

    severe_threshold: float = -50.0
    active_drying_threshold: float = -20.0
    stable_threshold: float = 0.0


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

    reference_lalo: list[float] = Field(default=[-2.496900, 114.312148])
    tropospheric_correction: str = "ERA5"
    unwrap_error_correction: str = "bridging+phase_closure"
    network_modification: MintPyNetworkConfig = Field(default_factory=MintPyNetworkConfig)


class PeatGuardConfig(BaseModel):
    """Root configuration for the PeatGuard pipeline."""

    aoi: AOIConfig
    sentinel1: Sentinel1Config = Field(default_factory=Sentinel1Config)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    mintpy: MintPyConfig = Field(default_factory=MintPyConfig)


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
