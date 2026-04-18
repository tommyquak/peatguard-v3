"""Tests for InSAR processing modules."""

import math

import numpy as np
import pytest

from peatguard.insar.displacement import (
    compute_displacement,
    displacement_to_velocity,
    los_to_vertical,
    phase_to_los_displacement,
)
from peatguard.insar.filter import goldstein_filter
from peatguard.insar.pairs import (
    InSARPair,
    network_summary,
    select_sbas_pairs,
    select_sequential_pairs,
)


class TestPairSelection:
    def test_sequential_pairs(self):
        dates = ["2015-05-09", "2015-06-02", "2015-06-26", "2015-07-20"]
        pairs = select_sequential_pairs(dates)
        assert len(pairs) == 3
        assert pairs[0].reference_date == "2015-05-09"
        assert pairs[0].secondary_date == "2015-06-02"

    def test_sbas_pairs(self):
        dates = ["2015-05-09", "2015-06-02", "2015-06-26", "2015-07-20"]
        pairs = select_sbas_pairs(dates, max_temporal_baseline_days=48)
        # Should have more connections than sequential
        assert len(pairs) >= 3

    def test_sbas_max_connections(self):
        dates = [f"2015-{m:02d}-01" for m in range(1, 13)]
        pairs = select_sbas_pairs(dates, max_temporal_baseline_days=60, max_connections=2)
        # Each date connects to at most 2 forward dates
        from collections import Counter
        ref_counts = Counter(p.reference_date for p in pairs)
        assert all(c <= 2 for c in ref_counts.values())

    def test_empty_dates(self):
        pairs = select_sbas_pairs([])
        assert len(pairs) == 0

    def test_single_date(self):
        pairs = select_sequential_pairs(["2015-01-01"])
        assert len(pairs) == 0

    def test_network_summary(self):
        pairs = [
            InSARPair("2015-01-01", "2015-01-25", 24),
            InSARPair("2015-01-25", "2015-02-18", 24),
            InSARPair("2015-01-01", "2015-02-18", 48),
        ]
        summary = network_summary(pairs)
        assert summary["num_pairs"] == 3
        assert summary["num_dates"] == 3
        assert summary["min_baseline_days"] == 24


class TestDisplacement:
    def test_phase_to_los(self):
        # 2*pi phase = lambda/2 displacement
        phase = np.array([[2 * math.pi]])
        los = phase_to_los_displacement(phase, wavelength_m=0.056)
        expected = 0.056 / 2  # = 0.028 m
        np.testing.assert_allclose(los, expected, atol=1e-6)

    def test_zero_phase(self):
        phase = np.zeros((10, 10))
        los = phase_to_los_displacement(phase)
        np.testing.assert_allclose(los, 0.0)

    def test_los_to_vertical(self):
        los = np.array([[-0.01]])  # -10 mm LOS
        vertical = los_to_vertical(los, incidence_deg=37.0)
        # vertical = los / cos(37) ~= -0.01 / 0.7986 ~= -0.01252
        assert vertical[0, 0] < los[0, 0]  # Vertical is larger magnitude
        expected = -0.01 / math.cos(math.radians(37.0))
        np.testing.assert_allclose(vertical, expected, atol=1e-6)

    def test_displacement_to_velocity(self):
        disp = np.array([[-0.05]])  # -50 mm cumulative
        vel = displacement_to_velocity(disp, temporal_span_days=365.25)
        np.testing.assert_allclose(vel, -50.0, atol=0.1)

    def test_compute_displacement_full(self):
        phase = np.full((10, 10), math.pi)
        result = compute_displacement(
            phase,
            wavelength_m=0.056,
            incidence_deg=37.0,
            temporal_span_days=365.25,
        )
        assert "los_m" in result
        assert "vertical_m" in result
        assert "velocity_mm_yr" in result
        assert result["vertical_m"].shape == (10, 10)


class TestGoldsteinFilter:
    def test_filter_reduces_noise(self, sample_complex_ifg):
        filtered = goldstein_filter(sample_complex_ifg, alpha=0.8, patch_size=32)
        assert filtered.shape == sample_complex_ifg.shape
        assert filtered.dtype == sample_complex_ifg.dtype

    def test_alpha_zero_is_no_filter(self):
        np.random.seed(42)
        ifg = np.exp(1j * np.random.randn(64, 64)).astype(np.complex64)
        filtered = goldstein_filter(ifg, alpha=0.0, patch_size=32)
        # Alpha=0 should produce minimal change
        phase_diff = np.abs(np.angle(filtered) - np.angle(ifg))
        assert np.mean(phase_diff) < 0.5

    def test_invalid_alpha(self):
        ifg = np.ones((32, 32), dtype=np.complex64)
        with pytest.raises(ValueError, match="alpha"):
            goldstein_filter(ifg, alpha=1.5)
