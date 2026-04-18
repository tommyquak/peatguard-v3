"""Tests for configuration loading and validation."""

from pathlib import Path

import pytest

from peatguard.config import PeatGuardConfig, load_config


def test_load_default_config():
    config_path = Path(__file__).parent.parent / "config" / "default.yaml"
    config = load_config(config_path)
    assert isinstance(config, PeatGuardConfig)
    assert config.aoi.epsg == 32649
    assert len(config.aoi.bbox) == 4


def test_bbox_validation():
    with pytest.raises(ValueError, match="west.*less than east"):
        PeatGuardConfig(aoi={"bbox": [115.0, -2.6, 114.0, -2.4], "epsg": 32649})


def test_bbox_wrong_length():
    with pytest.raises(ValueError, match="exactly 4"):
        PeatGuardConfig(aoi={"bbox": [114.0, -2.6, 115.0], "epsg": 32649})


def test_processing_defaults():
    config_path = Path(__file__).parent.parent / "config" / "default.yaml"
    config = load_config(config_path)
    assert config.processing.wavelength_m == 0.056
    assert config.processing.incidence_deg == 37.0
    assert config.processing.coherence_threshold == 0.3


def test_classification_thresholds():
    config_path = Path(__file__).parent.parent / "config" / "default.yaml"
    config = load_config(config_path)
    assert config.classification.severe_threshold == -50.0
    assert config.classification.active_drying_threshold == -20.0
    assert config.classification.moderate_drying_threshold == -5.0
    assert config.classification.stable_threshold == 5.0


def test_export_settings():
    config_path = Path(__file__).parent.parent / "config" / "default.yaml"
    config = load_config(config_path)
    assert config.export.cog_blocksize == 512
    assert config.export.cog_compression == "DEFLATE"
    assert config.export.overview_levels == [2, 4, 8, 16]
