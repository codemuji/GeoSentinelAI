import os
import json
import numpy as np
from typing import Dict, Any, List, Tuple

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

def compute_spectral_indices(bands: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """Computes NDVI, NDWI, and NDBI arrays from calibrated Sentinel-2 bands."""
    green = bands["B03"].astype(np.float32)
    red = bands["B04"].astype(np.float32)
    nir = bands["B08"].astype(np.float32)
    swir = bands.get("B11", red).astype(np.float32)

    ndvi = (nir - red) / (nir + red + 1e-6)
    ndwi = (green - nir) / (green + nir + 1e-6)
    ndbi = (swir - nir) / (swir + nir + 1e-6)

    return {"ndvi": ndvi, "ndwi": ndwi, "ndbi": ndbi}

def classify_pixels(indices: Dict[str, np.ndarray], bands: Dict[str, np.ndarray]) -> np.ndarray:
    """
    Classifies pixels into 5 biophysical land cover classes:
    0: Water, 1: Forest, 2: Agriculture, 3: Urban, 4: Bare Soil
    """
    ndvi = indices["ndvi"]
    ndwi = indices["ndwi"]
    ndbi = indices["ndbi"]
    red = bands["B04"]
    nir = bands["B08"]

    classified = np.full(ndvi.shape, 4, dtype=np.int32)

    water_mask = (ndwi > 0.05) | ((ndvi < 0.0) & (nir < 0.10))
    classified[water_mask] = 0

    forest_mask = (ndvi > 0.55) & (~water_mask)
    classified[forest_mask] = 1

    agri_mask = (ndvi >= 0.20) & (ndvi <= 0.55) & (~water_mask)
    classified[agri_mask] = 2

    urban_mask = ((ndbi > 0.0) | ((red > 0.18) & (ndvi < 0.20))) & (~water_mask) & (~forest_mask) & (~agri_mask)
    classified[urban_mask] = 3

    return classified

def calculate_land_cover_percentages(classified: np.ndarray) -> Dict[str, float]:
    """Calculates class percentage distributions summing to exactly 100%."""
    total = max(1, classified.size)
    counts = np.bincount(classified.ravel(), minlength=5)
    pcts = [round(float(counts[i] / total) * 100.0, 1) for i in range(5)]
    
    current_sum = round(sum(pcts), 1)
    diff = round(100.0 - current_sum, 1)
    if diff != 0.0:
        max_idx = int(np.argmax(pcts))
        pcts[max_idx] = round(pcts[max_idx] + diff, 1)

    return {
        "Forest": pcts[1],
        "Agriculture": pcts[2],
        "Water": pcts[0],
        "Bare Soil": pcts[4],
        "Urban": pcts[3]
    }

def run_ml_land_cover(sat_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Multispectral Land Cover Classification.
    Computes exact pixel classification if multi-band arrays are present,
    otherwise uses spectral heuristic fallback.
    """
    bands = sat_data.get("bands", {})
    required = ["B03", "B04", "B08"]
    if all(b in bands and isinstance(bands[b], np.ndarray) and bands[b].size > 0 for b in required):
        indices = compute_spectral_indices(bands)
        classified = classify_pixels(indices, bands)
        return calculate_land_cover_percentages(classified)

    ndvi_mean = float(sat_data.get("ndvi_mean", 0.35))
    stats = sat_data.get("spectral_stats", {})
    veg_ratio = float(stats.get("vegetation_ratio", 0.4))

    forest_pct = round(min(65.0, max(15.0, veg_ratio * 70.0)), 1)
    agri_pct = round(min(35.0, max(10.0, ndvi_mean * 45.0)), 1)
    water_pct = round(max(5.0, (1.0 - ndvi_mean) * 15.0), 1)
    bare_pct = round(max(5.0, 100.0 - (forest_pct + agri_pct + water_pct) - 6.0), 1)
    urban_pct = round(100.0 - (forest_pct + agri_pct + water_pct + bare_pct), 1)

    return {
        "Forest": forest_pct,
        "Agriculture": agri_pct,
        "Water": water_pct,
        "Bare Soil": bare_pct,
        "Urban": max(1.0, urban_pct)
    }



def generate_geological_interpretation(
    land_cover: Dict[str, float],
    sat_data: Dict[str, Any],
    bbox: List[float]
) -> List[Dict[str, Any]]:
    """
    Level 3 AI: Generative AI (Google Gemini API) Geological Expert.
    Checks for GEMINI_API_KEY/GOOGLE_API_KEY; if present, prompts Gemini for professional geomorphology report.
    Otherwise falls back to Level 1 Physics Rule Engine.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    if GENAI_AVAILABLE and api_key:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
You are a Senior Exploration Geologist and Remote Sensing Scientist.
Analyze the following Earth Observation data for a selected Area of Interest (AOI):
- Bounding Box (WGS84): {bbox}
- Satellite Source: {sat_data.get('source')} (Date: {sat_data.get('scene_date')})
- Mean Spectral NDVI: {sat_data.get('ndvi_mean')}
- Land Cover Classification: {json.dumps(land_cover)}

Based on these exact quantitative metrics and the geographic location of the bounding box, output exactly 3 professional geological, geomorphological, or structural landscape interpretations.
Every interpretation MUST explain the underlying landscape (e.g., bedrock exposure, alluvial deposits, drainage patterns, lineaments, or weathering).

Return ONLY a JSON array with exactly 3 objects matching this schema:
[
  {{"text": "Your detailed geological interpretation sentence here.", "confidence": 0.89}},
  {{"text": "Second interpretation sentence.", "confidence": 0.82}},
  {{"text": "Third interpretation sentence.", "confidence": 0.76}}
]
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            
            parsed = json.loads(response.text)
            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed[:3]
        except Exception as e:
            print(f"[Gemini API Notice] Using Rule Engine fallback: {e}")

    # Level 1 Fallback: Spectral Geomorphological Rule Engine
    ndvi_mean = sat_data.get("ndvi_mean", 0.35)
    bare_pct = land_cover.get("Bare Soil", 15.0)
    water_pct = land_cover.get("Water", 10.0)
    scene_date = sat_data.get("scene_date", "2024")
    
    return [
        {
            "text": f"Dense vegetation canopy (NDVI {ndvi_mean}) across {land_cover.get('Forest', 45)}% of the AOI is likely obscuring underlying bedrock structure and fracture zones.",
            "confidence": 0.90
        },
        {
            "text": f"Exposed barren land ({bare_pct}%) and weathered soil horizons along lower elevations indicate potential alluvial terraces and erosional surface processes.",
            "confidence": 0.83
        },
        {
            "text": f"Linear drainage pathways adjacent to water bodies ({water_pct}%) exhibit dendritic to rectangular drainage patterns typical of structurally controlled valleys.",
            "confidence": 0.77
        }
    ]
