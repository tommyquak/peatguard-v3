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
    classify_subsidence,
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
