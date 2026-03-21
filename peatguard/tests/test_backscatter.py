"""Tests for backscatter processing modules."""

import numpy as np
import pytest

from peatguard.backscatter.speckle import lee_sigma_filter


class TestLeeFilter:
    def test_reduces_variance(self):
        np.random.seed(42)
        noisy = np.random.exponential(1.0, size=(100, 100)).astype(np.float32)
        filtered = lee_sigma_filter(noisy, window_size=7)

        assert filtered.shape == noisy.shape
        assert np.var(filtered) < np.var(noisy)

    def test_preserves_shape(self):
        data = np.ones((50, 50), dtype=np.float32)
        filtered = lee_sigma_filter(data, window_size=7)
        np.testing.assert_allclose(filtered, data, atol=0.01)

    def test_odd_window_required(self):
        data = np.ones((50, 50), dtype=np.float32)
        with pytest.raises(ValueError, match="odd"):
            lee_sigma_filter(data, window_size=6)

    def test_edge_handling(self):
        data = np.random.randn(20, 20).astype(np.float32)
        filtered = lee_sigma_filter(data, window_size=7)
        # No NaN or inf at edges
        assert np.all(np.isfinite(filtered))
