"""Tests for COG export and metadata generation."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from peatguard.export.cog import write_cog, write_cog_from_bounds, read_raster


class TestCOGWriter:
    def test_write_2d_array(self, tmp_output):
        data = np.random.randn(100, 100).astype(np.float32)
        transform = from_origin(114.3, -2.5, 0.001, 0.001)

        path = write_cog(
            data=data,
            output_path=tmp_output / "test.tif",
            crs=32649,
            transform=transform,
        )

        assert path.exists()
        with rasterio.open(path) as src:
            assert src.count == 1
            assert src.crs.to_epsg() == 32649
            assert src.width == 100
            assert src.height == 100
            # Check tiling
            assert src.profile["tiled"] is True

    def test_write_3d_array(self, tmp_output):
        data = np.random.randn(3, 50, 50).astype(np.float32)
        transform = from_origin(114.3, -2.5, 0.001, 0.001)

        path = write_cog(
            data=data,
            output_path=tmp_output / "multi.tif",
            crs=32649,
            transform=transform,
            band_names=["band1", "band2", "band3"],
        )

        with rasterio.open(path) as src:
            assert src.count == 3
            assert src.descriptions[0] == "band1"

    def test_write_cog_from_bounds(self, tmp_output):
        data = np.random.randn(100, 100).astype(np.float32)
        bounds = (114.304, -2.611, 114.404, -2.511)

        path = write_cog_from_bounds(
            data=data,
            output_path=tmp_output / "bounded.tif",
            crs=4326,
            bounds=bounds,
        )

        with rasterio.open(path) as src:
            assert abs(src.bounds.left - 114.304) < 0.01
            assert abs(src.bounds.bottom - (-2.611)) < 0.01

    def test_nodata_handling(self, tmp_output):
        data = np.full((50, 50), -9999.0, dtype=np.float32)
        transform = from_origin(0, 0, 1, 1)

        path = write_cog(
            data=data,
            output_path=tmp_output / "nodata.tif",
            crs=32649,
            transform=transform,
            nodata=-9999.0,
        )

        with rasterio.open(path) as src:
            assert src.nodata == -9999.0

    def test_overviews_created(self, tmp_output):
        data = np.random.randn(512, 512).astype(np.float32)
        transform = from_origin(114.3, -2.5, 0.0001, 0.0001)

        path = write_cog(
            data=data,
            output_path=tmp_output / "overview.tif",
            crs=32649,
            transform=transform,
        )

        with rasterio.open(path) as src:
            assert len(src.overviews(1)) > 0


class TestReadRaster:
    def test_roundtrip(self, tmp_output):
        original = np.random.randn(50, 50).astype(np.float32)
        transform = from_origin(114.3, -2.5, 0.001, 0.001)

        path = write_cog(
            data=original,
            output_path=tmp_output / "roundtrip.tif",
            crs=32649,
            transform=transform,
            nodata=-9999.0,
        )

        data, metadata = read_raster(path)
        assert data.shape == (1, 50, 50)
        np.testing.assert_allclose(data[0], original, atol=1e-6)
        assert metadata["crs"].to_epsg() == 32649
