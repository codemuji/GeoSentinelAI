import pytest
from backend.services.engine import (
    get_regional_context,
    generate_dynamic_geomorphology_rules,
    generate_geological_interpretation
)

def test_regional_context_resolution():
    """Verifies that regional context returns a descriptive string for coordinate boundaries."""
    tawang_bbox = [91.85, 27.58, 91.87, 27.60] # Eastern Himalayas
    context = get_regional_context(tawang_bbox)
    assert isinstance(context, str)
    assert len(context) > 0
    assert any(k in context for k in ["Tawang", "Arunachal", "Himalaya", "27."])

def test_dynamic_geomorphology_rules_adapt_to_land_cover():
    """Verifies that dynamic rule fallback adapts interpretations based on land cover ratios."""
    # Scenario 1: Rocky / Mountainous terrain with high bare soil
    rocky_cover = {"Forest": 5.0, "Agriculture": 2.0, "Water": 3.0, "Bare Soil": 85.0, "Urban": 5.0}
    rocky_sat = {"ndvi_mean": 0.08, "source": "Sentinel-2"}
    rocky_results = generate_dynamic_geomorphology_rules(rocky_cover, rocky_sat, "Eastern Himalayas")
    
    assert len(rocky_results) == 3
    # Should highlight bedrock exposure or rock weathering
    texts = " ".join(r["text"] for r in rocky_results).lower()
    assert "bedrock" in texts or "weather" in texts or "litholog" in texts or "erosion" in texts

    # Scenario 2: River Basin with high water
    water_cover = {"Forest": 10.0, "Agriculture": 15.0, "Water": 65.0, "Bare Soil": 5.0, "Urban": 5.0}
    water_sat = {"ndvi_mean": -0.15, "source": "Sentinel-2"}
    water_results = generate_dynamic_geomorphology_rules(water_cover, water_sat, "Brahmaputra Valley")
    
    assert len(water_results) == 3
    water_texts = " ".join(r["text"] for r in water_results).lower()
    assert "alluvial" in water_texts or "drainage" in water_texts or "fluvial" in water_texts or "sediment" in water_texts

    # Verify rocky and water scenarios produce distinct interpretations
    assert rocky_results[0]["text"] != water_results[0]["text"]

def test_generate_geological_interpretation_contract():
    """Verifies end-to-end generate_geological_interpretation contract in offline mode."""
    cover = {"Forest": 45.0, "Agriculture": 25.0, "Water": 10.0, "Bare Soil": 15.0, "Urban": 5.0}
    sat = {"ndvi_mean": 0.42, "scene_date": "2024-06-15", "source": "Sentinel-2 L2A"}
    bbox = [91.85, 27.58, 91.87, 27.60]
    
    results = generate_geological_interpretation(cover, sat, bbox)
    assert len(results) == 3
    for item in results:
        assert "text" in item and len(item["text"]) > 15
        assert "confidence" in item
        assert 0.60 <= item["confidence"] <= 1.0
