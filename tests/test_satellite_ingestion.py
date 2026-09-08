import pytest
import numpy as np
from rasterio.crs import CRS
from rasterio.transform import from_origin
from backend.services.satellite import (
    reproject_bbox,
    calculate_raster_window,
    read_band_window,
    fetch_sentinel2_data
)

def test_reproject_bbox_wgs84_to_utm():
    """Verifies that WGS84 [minx, miny, maxx, maxy] correctly reprojects to UTM CRS."""
    wgs84_bbox = [91.85, 27.58, 91.87, 27.60]
    utm_crs = CRS.from_epsg(32645) # UTM Zone 45N
    
    proj_bbox = reproject_bbox(wgs84_bbox, utm_crs)
    assert len(proj_bbox) == 4
    minx, miny, maxx, maxy = proj_bbox
    assert minx < maxx
    assert miny < maxy
    # UTM coordinates in Zone 45N are in hundreds of thousands to millions of meters
    assert minx > 100000
    assert miny > 1000000

def test_calculate_raster_window_bounded():
    """Verifies window calculation from projected coordinates and affine transform."""
    transform = from_origin(900000, 3100000, 10, 10) # 10m pixel size
    proj_bbox = [910000, 3050000, 920000, 3060000]
    
    window = calculate_raster_window(proj_bbox, transform, max_dim=256)
    assert window.width > 0
    assert window.height > 0
    assert window.width <= 256
    assert window.height <= 256

def test_cloud_warning_threshold():
    """Verifies cloud_warning logic in fallback / metadata generator."""
    from backend.services.satellite import _format_satellite_metadata
    
    low_cloud = _format_satellite_metadata(
        scene_id="S2A_TEST_LOW",
        scene_date="2024-06-15",
        cloud_cover=12.0,
        ndvi_mean=0.45,
        spectral_stats={},
        bbox=[0, 0, 1, 1],
        bands={}
    )
    assert low_cloud["cloud_warning"] is False

    high_cloud = _format_satellite_metadata(
        scene_id="S2A_TEST_HIGH",
        scene_date="2024-06-15",
        cloud_cover=42.5,
        ndvi_mean=0.25,
        spectral_stats={},
        bbox=[0, 0, 1, 1],
        bands={}
    )
    assert high_cloud["cloud_warning"] is True
