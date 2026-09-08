from starlette.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_analyze_endpoint_contract(mock_aoi_geojson, monkeypatch):
    """Verifies that the /api/analyze endpoint conforms to the agreed schema contract offline."""
    mock_sat_response = {
        "status": "success",
        "scene_id": "S2A_MSIL2A_20240615T042701_TEST",
        "scene_date": "2024-06-15",
        "cloud_cover": 14.2,
        "source": "Sentinel-2 L2A (Test Fixture)",
        "ndvi_mean": 0.42,
        "spectral_stats": {"min_ndvi": 0.05, "max_ndvi": 0.78, "vegetation_ratio": 0.45},
        "bbox": [91.85, 27.58, 91.87, 27.60]
    }
    monkeypatch.setattr("backend.main.fetch_sentinel2_data", lambda aoi, date: mock_sat_response)

    payload = {
        "aoi": mock_aoi_geojson,
        "date": "2024-06-15"
    }
    
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    # 1. Assert land cover percentages
    assert "land_cover" in data
    land_cover = data["land_cover"]
    expected_classes = ["Forest", "Agriculture", "Water", "Bare Soil", "Urban"]
    for cls in expected_classes:
        assert cls in land_cover, f"Missing class '{cls}' in land_cover response"
        assert isinstance(land_cover[cls], (int, float))
    total_pct = sum(land_cover.values())
    assert 99.0 <= total_pct <= 101.0, f"Land cover percentages sum to {total_pct}, expected ~100"
    
    # 2. Assert interpretations
    assert "interpretations" in data
    interpretations = data["interpretations"]
    assert len(interpretations) == 3
    for item in interpretations:
        assert "text" in item and len(item["text"]) > 0
        assert "confidence" in item
        assert 0.0 <= item["confidence"] <= 1.0
        
    # 3. Assert AOI size
    assert "aoi_size_km2" in data
    assert data["aoi_size_km2"] > 0
    
    # 4. Assert satellite info provenance
    assert "satellite_info" in data
    sat_info = data["satellite_info"]
    assert sat_info["scene_id"] == "S2A_MSIL2A_20240615T042701_TEST"
    assert sat_info["cloud_cover"] == 14.2
    assert sat_info["ndvi_mean"] == 0.42
    
    # 5. Assert cloud warning flag (cloud_cover 14.2 <= 30.0 -> False)
    assert "cloud_warning" in data
    assert data["cloud_warning"] is False

    # 6. Assert literature list is present and structured
    assert "literature" in data
    assert isinstance(data["literature"], list)

def test_analyze_endpoint_cloud_warning_triggered(mock_aoi_geojson, monkeypatch):
    """Verifies that cloud_warning is True when cloud_cover > 30%."""
    mock_cloudy_response = {
        "status": "success",
        "scene_id": "S2A_MSIL2A_20240615T042701_CLOUDY",
        "scene_date": "2024-06-15",
        "cloud_cover": 45.8,
        "source": "Sentinel-2 L2A (Cloudy)",
        "ndvi_mean": 0.28,
        "spectral_stats": {"min_ndvi": 0.0, "max_ndvi": 0.5, "vegetation_ratio": 0.2},
        "bbox": [91.85, 27.58, 91.87, 27.60]
    }
    monkeypatch.setattr("backend.main.fetch_sentinel2_data", lambda aoi, date: mock_cloudy_response)

    payload = {"aoi": mock_aoi_geojson, "date": "2024-06-15"}
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    assert response.json()["cloud_warning"] is True

def test_synthetic_spectral_fixtures_structure(synthetic_spectral_fixtures):
    """Verifies synthetic 4-band spectral arrays are available and shaped correctly."""
    required_bands = ["B03", "B04", "B08", "B11"]
    for surface_type, bands in synthetic_spectral_fixtures.items():
        for band in required_bands:
            assert band in bands, f"Missing band {band} in {surface_type} fixture"
            assert bands[band].shape == (10, 10)
            assert bands[band].dtype == "float32"
