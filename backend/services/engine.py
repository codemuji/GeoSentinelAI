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

def run_ml_land_cover(sat_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Multispectral Land Cover Classification.
    Computes class percentages based on spectral indices and band distributions.
    """
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
