import pytest
import numpy as np
from backend.services.engine import (
    compute_spectral_indices,
    classify_pixels,
    calculate_land_cover_percentages,
    run_ml_land_cover,
    generate_imagery_overlays
)

def test_compute_spectral_indices():
    """Verifies that NDVI, NDWI, and NDBI are computed correctly."""
    shape = (5, 5)
    bands = {
        "B03": np.full(shape, 0.10, dtype=np.float32), # Green
        "B04": np.full(shape, 0.05, dtype=np.float32), # Red
        "B08": np.full(shape, 0.45, dtype=np.float32), # NIR
        "B11": np.full(shape, 0.20, dtype=np.float32)  # SWIR
    }
    indices = compute_spectral_indices(bands)
    
    assert "ndvi" in indices
    assert "ndwi" in indices
    assert "ndbi" in indices
    
    # Expected NDVI: (0.45 - 0.05) / (0.45 + 0.05) = 0.40 / 0.50 = 0.80
    assert np.isclose(indices["ndvi"][0, 0], 0.80, atol=0.01)
    
    # Expected NDWI: (0.10 - 0.45) / (0.10 + 0.45) = -0.35 / 0.55 = -0.636
    assert np.isclose(indices["ndwi"][0, 0], -0.636, atol=0.01)
    
    # Expected NDBI: (0.20 - 0.45) / (0.20 + 0.45) = -0.25 / 0.65 = -0.384
    assert np.isclose(indices["ndbi"][0, 0], -0.384, atol=0.01)

def test_classify_pure_water_fixture(synthetic_spectral_fixtures):
    """Verifies that pure water spectral fixture classifies as 100% Water."""
    water_bands = synthetic_spectral_fixtures["water"]
    sat_data = {"bands": water_bands, "ndvi_mean": -0.3}
    
    land_cover = run_ml_land_cover(sat_data)
    assert land_cover["Water"] > 95.0
    assert sum(land_cover.values()) == 100.0

def test_classify_dense_forest_fixture(synthetic_spectral_fixtures):
    """Verifies that dense vegetation spectral fixture classifies as 100% Forest."""
    forest_bands = synthetic_spectral_fixtures["forest"]
    sat_data = {"bands": forest_bands, "ndvi_mean": 0.85}
    
    land_cover = run_ml_land_cover(sat_data)
    assert land_cover["Forest"] > 95.0
    assert sum(land_cover.values()) == 100.0

def test_classify_urban_fixture(synthetic_spectral_fixtures):
    """Verifies that urban spectral fixture classifies as majority Urban."""
    urban_bands = synthetic_spectral_fixtures["urban"]
    sat_data = {"bands": urban_bands, "ndvi_mean": 0.15}
    
    land_cover = run_ml_land_cover(sat_data)
    assert land_cover["Urban"] > 80.0
    assert sum(land_cover.values()) == 100.0

def test_generate_imagery_overlays(synthetic_spectral_fixtures):
    """Verifies generation of RGB and NDVI PNG data URLs and Leaflet image bounds."""
    forest_bands = synthetic_spectral_fixtures["forest"]
    sat_data = {"bands": forest_bands, "ndvi_mean": 0.85}
    bbox = [91.85, 27.58, 91.87, 27.60]
    
    overlays = generate_imagery_overlays(sat_data, bbox)
    assert "rgb_image" in overlays
    assert "ndvi_image" in overlays
    assert "image_bounds" in overlays
    
    assert overlays["rgb_image"].startswith("data:image/png;base64,")
    assert overlays["ndvi_image"].startswith("data:image/png;base64,")
    # Leaflet bounds order: [[min_lat, min_lon], [max_lat, max_lon]]
    assert overlays["image_bounds"] == [[27.58, 91.85], [27.60, 91.87]]

