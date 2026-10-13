import pytest
import numpy as np
from starlette.testclient import TestClient
from backend.main import app
from backend.services.engine import (
    compute_mariculture_intelligence,
    generate_imagery_overlays,
    create_synthetic_terrain_bands
)

client = TestClient(app)

def test_mariculture_inland_deactivation():
    """Verifies that an inland terrestrial AOI deactivates mariculture analysis."""
    land_cover = {"Water": 0.5, "Forest": 45.0, "Agriculture": 30.0, "Bare Soil": 24.5, "Urban": 0.0}
    sat_data = {"ndvi_mean": 0.55, "cloud_cover": 5.0}
    # Centroid in Himalayan inland sector
    bbox = [91.80, 27.50, 91.90, 27.60]
    
    intel = compute_mariculture_intelligence(land_cover, sat_data, aoi_size_km2=20.0, bbox=bbox)
    assert intel["is_coastal"] is False
    assert intel["suitability_score"] == 0.0
    assert intel["wet_biomass_annual_tonnes"] == 0.0
    assert "inland terrestrial" in intel["summary"].lower()

def test_mariculture_palk_bay_coastal_hub():
    """Verifies that an AOI in Palk Bay / Gulf of Mannar calculates high suitability and blue carbon sequestration."""
    land_cover = {"Water": 85.0, "Bare Soil": 10.0, "Forest": 0.0, "Agriculture": 5.0, "Urban": 0.0}
    sat_data = {"ndvi_mean": 0.08, "cloud_cover": 4.0}
    # Palk Bay / Mandapam (Tamil Nadu)
    bbox = [79.10, 9.25, 79.20, 9.35]
    
    intel = compute_mariculture_intelligence(land_cover, sat_data, aoi_size_km2=15.0, bbox=bbox)
    assert intel["is_coastal"] is True
    assert intel["suitability_score"] >= 80.0
    assert "OPTIMAL" in intel["feasibility_tier"]
    assert len(intel["recommended_species"]) >= 2
    assert "Kappaphycus alvarezii" in intel["recommended_species"][0]
    assert intel["water_area_ha"] > 100.0
    assert intel["wet_biomass_annual_tonnes"] > 0.0
    assert intel["co2_sequestered_t_annual"] > 0.0
    assert intel["coastal_jobs_supported"] >= 10

def test_fai_raster_overlay_generation():
    """Verifies that generate_imagery_overlays produces a valid base64 FAI image."""
    bbox = [79.10, 9.25, 79.20, 9.35]
    sat_data = {"ndvi_mean": 0.08, "cloud_cover": 5.0}
    
    overlays = generate_imagery_overlays(sat_data, bbox)
    assert "fai_image" in overlays
    assert overlays["fai_image"].startswith("data:image/png;base64,")
    assert "rgb_image" in overlays
    assert "ndvi_image" in overlays
    assert len(overlays["image_bounds"]) == 2

def test_api_analyze_returns_mariculture_and_fai():
    """Verifies that the /api/analyze endpoint includes mariculture and FAI in the contract."""
    payload = {
        "aoi": {
            "type": "Polygon",
            "coordinates": [[[79.10, 9.25], [79.20, 9.25], [79.20, 9.35], [79.10, 9.35], [79.10, 9.25]]]
        },
        "date": "2024-06-15"
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "fai_image" in data
    assert data["fai_image"] is not None
    assert "mariculture" in data
    assert data["mariculture"] is not None
    assert data["mariculture"]["is_coastal"] is True
    assert data["mariculture"]["co2_sequestered_t_annual"] > 0

def test_health_endpoints():
    """Verifies /health and /api/health."""
    res1 = client.get("/health")
    assert res1.status_code == 200
    assert res1.json()["status"] == "ok"

    res2 = client.get("/api/health")
    assert res2.status_code == 200
    assert res2.json()["service"] == "GeoSentinelAI"
