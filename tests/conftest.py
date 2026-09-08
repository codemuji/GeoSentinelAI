import pytest
import numpy as np

@pytest.fixture
def mock_aoi_geojson():
    """Sample WGS84 GeoJSON polygon for Tawang, Arunachal Pradesh."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [91.8500, 27.5800],
                    [91.8700, 27.5800],
                    [91.8700, 27.6000],
                    [91.8500, 27.6000],
                    [91.8500, 27.5800]
                ]
            ]
        },
        "properties": {}
    }

@pytest.fixture
def synthetic_spectral_fixtures():
    """
    Returns deterministic 10x10 synthetic 4-band arrays for:
    water, dense_forest, agriculture, urban, bare_soil
    Bands: B03 (Green), B04 (Red), B08 (NIR), B11 (SWIR)
    """
    shape = (10, 10)
    
    # Pure Water (high green, very low NIR/SWIR)
    water = {
        "B03": np.full(shape, 0.18, dtype=np.float32),
        "B04": np.full(shape, 0.08, dtype=np.float32),
        "B08": np.full(shape, 0.03, dtype=np.float32),
        "B11": np.full(shape, 0.01, dtype=np.float32)
    }

    # Dense Forest (very high NIR, low Red)
    forest = {
        "B03": np.full(shape, 0.05, dtype=np.float32),
        "B04": np.full(shape, 0.03, dtype=np.float32),
        "B08": np.full(shape, 0.55, dtype=np.float32),
        "B11": np.full(shape, 0.10, dtype=np.float32)
    }

    # Agriculture (moderate NIR and Red)
    agri = {
        "B03": np.full(shape, 0.10, dtype=np.float32),
        "B04": np.full(shape, 0.12, dtype=np.float32),
        "B08": np.full(shape, 0.32, dtype=np.float32),
        "B11": np.full(shape, 0.18, dtype=np.float32)
    }

    # Urban / Built-up (high SWIR, NDBI > 0)
    urban = {
        "B03": np.full(shape, 0.20, dtype=np.float32),
        "B04": np.full(shape, 0.25, dtype=np.float32),
        "B08": np.full(shape, 0.22, dtype=np.float32),
        "B11": np.full(shape, 0.38, dtype=np.float32)
    }

    # Bare Soil / Rock (moderate reflectance, low positive NDVI)
    soil = {
        "B03": np.full(shape, 0.16, dtype=np.float32),
        "B04": np.full(shape, 0.28, dtype=np.float32),
        "B08": np.full(shape, 0.31, dtype=np.float32),
        "B11": np.full(shape, 0.25, dtype=np.float32)
    }

    return {
        "water": water,
        "forest": forest,
        "agriculture": agri,
        "urban": urban,
        "soil": soil
    }
