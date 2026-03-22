"""Tests for analysis modules."""

import numpy as np
import pytest

from peatguard.analysis.canal_detect import (
    analyze_subsidence_by_distance,
    compute_canal_distance,
    threshold_canals,
)
from peatguard.analysis.deramp import deramp, fit_ramp
from peatguard.analysis.risk_score import (
    compute_combined_risk,
    compute_proximity_risk,
    compute_subsidence_risk,
)
from peatguard.analysis.subsidence_class import (
    CLASS_ACTIVE_DRYING,
    CLASS_NOISE_UPLIFT,
    CLASS_SEVERE,
    CLASS_STABLE,
    CLASS_WATER,
    classify_subsidence,
)
from peatguard.analysis.water_mask import (
    compute_water_mask_linear,
    compute_water_mask_vv,
    exclude_canals_from_water,
    morphological_cleanup_water,
    compute_ndvi,
    compute_mndwi,
)


class TestCanalDetection:
    def test_threshold_canals(self, sample_vv_backscatter):
        mask = threshold_canals(sample_vv_backscatter, percentile=15.0)
        assert mask.dtype == bool
        # Canals should be detected where we placed dark features
        assert mask[50, 50]  # Inside horizontal canal
        # Most canal pixels should be detected (may not be all due to percentile cutoff)
        canal_region = mask[45:55, :]
        assert canal_region.sum() > 0.5 * canal_region.size

    def test_canal_distance(self):
        mask = np.zeros((50, 50), dtype=bool)
        mask[25, :] = True  # Horizontal canal
        distance = compute_canal_distance(mask, pixel_resolution_m=10.0)
        assert distance[25, 0] == 0.0  # On canal
        assert abs(distance[26, 0] - 10.0) < 0.1  # 1 pixel away = 10m

    def test_subsidence_by_distance(self):
        subsidence = np.full((100, 100), -30.0)
        distance = np.arange(100).reshape(1, -1).repeat(100, axis=0).astype(float) * 10
        results = analyze_subsidence_by_distance(subsidence, distance)
        assert len(results) > 0
        assert all(r["mean_subsidence_mm_yr"] == pytest.approx(-30.0, abs=1.0) for r in results if r["pixel_count"] > 0)


class TestSubsidenceClassification:
    def test_classify_thresholds(self):
        velocity = np.array([[-60, -30, -10, 5]], dtype=np.float32)
        classified = classify_subsidence(velocity)
        assert classified[0, 0] == CLASS_SEVERE
        assert classified[0, 1] == CLASS_ACTIVE_DRYING
        assert classified[0, 2] == CLASS_STABLE
        assert classified[0, 3] == CLASS_NOISE_UPLIFT

    def test_nodata_handling(self):
        velocity = np.array([[-9999.0, -30.0]], dtype=np.float32)
        classified = classify_subsidence(velocity, nodata=-9999.0)
        assert classified[0, 0] == 0  # NoData class
        assert classified[0, 1] == CLASS_ACTIVE_DRYING


class TestRiskScore:
    def test_proximity_risk_decay(self):
        distance = np.array([[0, 100, 500, 1000, 2000]], dtype=np.float32)
        risk = compute_proximity_risk(distance, max_influence_m=1000.0)
        assert risk[0, 0] == pytest.approx(1.0)
        assert risk[0, -1] == 0.0  # Beyond influence
        # Monotonically decreasing
        assert all(risk[0, i] >= risk[0, i + 1] for i in range(risk.shape[1] - 1))

    def test_subsidence_risk_normalization(self):
        velocity = np.array([[-100, -50, -25, 0, 10]], dtype=np.float32)
        risk = compute_subsidence_risk(velocity, severe_threshold=-50.0)
        assert risk[0, 0] == pytest.approx(1.0)  # Capped at 1.0
        assert risk[0, 1] == pytest.approx(1.0)  # At threshold
        assert risk[0, 2] == pytest.approx(0.5)  # Half
        assert risk[0, 3] == pytest.approx(0.0)  # No subsidence
        assert risk[0, 4] == pytest.approx(0.0)  # Uplift

    def test_combined_risk(self):
        prox = np.array([[1.0, 0.0]], dtype=np.float32)
        subs = np.array([[0.0, 1.0]], dtype=np.float32)
        combined = compute_combined_risk(prox, subs, 0.4, 0.6)
        assert combined[0, 0] == pytest.approx(0.4)  # Only proximity
        assert combined[0, 1] == pytest.approx(0.6)  # Only subsidence


class TestWaterMask:
    def test_water_mask_vv_db(self):
        """Water pixels (< -20 dB) should be detected."""
        vv_db = np.array([[-25.0, -15.0, -30.0, -10.0, -9999.0]], dtype=np.float32)
        mask = compute_water_mask_vv(vv_db, threshold_db=-20.0, nodata=-9999.0)
        assert mask[0, 0] is np.True_   # -25 < -20 -> water
        assert mask[0, 1] is np.False_  # -15 > -20 -> not water
        assert mask[0, 2] is np.True_   # -30 < -20 -> water
        assert mask[0, 3] is np.False_  # -10 > -20 -> not water
        assert mask[0, 4] is np.False_  # nodata -> not water

    def test_water_mask_linear(self):
        """Linear scale: -20 dB = 0.01 linear power."""
        threshold_linear = 10.0 ** (-20.0 / 10.0)  # 0.01
        vv = np.array([[0.005, 0.05, 0.001, 0.1]], dtype=np.float32)
        mask = compute_water_mask_linear(vv, threshold_db=-20.0)
        assert mask[0, 0] is np.True_   # 0.005 < 0.01
        assert mask[0, 1] is np.False_  # 0.05 > 0.01
        assert mask[0, 2] is np.True_   # 0.001 < 0.01
        assert mask[0, 3] is np.False_  # 0.1 > 0.01

    def test_water_mask_linear_from_fixture(self, sample_vv_backscatter):
        """Canal regions in fixture have very low backscatter, should be detected as water."""
        mask = compute_water_mask_linear(sample_vv_backscatter, threshold_db=-20.0)
        assert mask.dtype == bool
        # The fixture has canal features at rows 45-55 and cols 20-25 with 0.05*0.05
        # scaling = very low values. These should be detected as water.
        canal_h_region = mask[45:55, :]
        assert canal_h_region.sum() > 0

    def test_exclude_canals(self):
        """Canal pixels should be removed from water mask."""
        water = np.zeros((10, 10), dtype=bool)
        water[3:7, :] = True  # Large water body
        canal = np.zeros((10, 10), dtype=bool)
        canal[5, :] = True  # Canal through the middle
        result = exclude_canals_from_water(water, canal)
        assert result[5, 0] is np.False_  # Canal pixel removed
        assert result[3, 0] is np.True_   # Non-canal water preserved

    def test_morphological_cleanup(self):
        """Small isolated detections should be removed."""
        mask = np.zeros((100, 100), dtype=bool)
        # Large water body (should survive cleanup)
        mask[20:40, 20:40] = True  # 400 pixels
        # Tiny noise (should be removed)
        mask[80, 80] = True  # 1 pixel
        cleaned = morphological_cleanup_water(mask, min_size_pixels=10, closing_radius=0)
        assert cleaned[30, 30] is np.True_    # Large body preserved
        assert cleaned[80, 80] is np.False_   # Noise removed

    def test_classify_with_water_mask(self):
        """Water mask should override subsidence classification."""
        velocity = np.array([[-60, -30, -10, 5]], dtype=np.float32)
        water = np.array([[True, False, False, True]], dtype=bool)
        classified = classify_subsidence(velocity, water_mask=water)
        assert classified[0, 0] == CLASS_WATER       # Was severe, now water
        assert classified[0, 1] == CLASS_ACTIVE_DRYING  # Not water, unchanged
        assert classified[0, 2] == CLASS_STABLE         # Not water, unchanged
        assert classified[0, 3] == CLASS_WATER       # Was noise/uplift, now water


class TestNDVI:
    def test_ndvi_values(self):
        """NDVI should range from -1 to 1 with expected values."""
        nir = np.array([[0.8, 0.1, 0.5, 0.0]], dtype=np.float32)
        red = np.array([[0.1, 0.8, 0.5, 0.0]], dtype=np.float32)
        ndvi = compute_ndvi(nir, red)
        # Dense vegetation: (0.8-0.1)/(0.8+0.1) = 0.778
        assert ndvi[0, 0] == pytest.approx(0.778, abs=0.01)
        # Water: (0.1-0.8)/(0.1+0.8) = -0.778
        assert ndvi[0, 1] == pytest.approx(-0.778, abs=0.01)
        # Bare soil: (0.5-0.5)/(0.5+0.5) = 0.0
        assert ndvi[0, 2] == pytest.approx(0.0, abs=0.01)


class TestMNDWI:
    def test_mndwi_water_positive(self):
        """MNDWI should be positive for water (green > SWIR)."""
        green = np.array([[0.3, 0.1]], dtype=np.float32)
        swir = np.array([[0.1, 0.3]], dtype=np.float32)
        mndwi = compute_mndwi(green, swir)
        assert mndwi[0, 0] > 0  # Water: green > SWIR
        assert mndwi[0, 1] < 0  # Vegetation: green < SWIR


class TestDeramp:
    def test_removes_linear_trend(self):
        rows, cols = 100, 100
        rr, cc = np.meshgrid(np.arange(rows, dtype=float), np.arange(cols, dtype=float), indexing="ij")
        ramp = 0.01 * rr + 0.02 * cc + 1.0
        signal = np.random.randn(rows, cols) * 0.1
        data = ramp + signal

        deramped = deramp(data.astype(np.float32))
        # After deramping, the mean should be near zero and the ramp removed
        assert abs(np.mean(deramped)) < 0.5

    def test_nodata_preserved(self):
        data = np.full((10, 10), -9999.0, dtype=np.float32)
        data[5, 5] = 1.0
        result = deramp(data, nodata=-9999.0)
        assert result[0, 0] == -9999.0
