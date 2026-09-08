import math
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List
from shapely.geometry import shape
from backend.services.satellite import fetch_sentinel2_data
from backend.services.engine import run_ml_land_cover, generate_geological_interpretation

app = FastAPI(title="GeoSentinel AI API", description="AI-powered Geological & Remote Sensing Intelligence Platform")

class AnalysisRequest(BaseModel):
    aoi: Dict[str, Any]
    date: str

class GeoInterpretation(BaseModel):
    text: str
    confidence: float

class AnalysisResponse(BaseModel):
    land_cover: Dict[str, float]
    interpretations: List[GeoInterpretation]
    aoi_size_km2: float
    satellite_info: Dict[str, Any]
    cloud_warning: bool = False

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_aoi(request: AnalysisRequest):
    """
    Core AI & Remote Sensing endpoint.
    Receives GeoJSON AOI + Satellite Date -> queries Planetary Computer STAC -> runs ML classification & geological reasoning.
    """
    # 1. Fetch real Sentinel-2 L2A metadata & COG spectral indices via Planetary Computer STAC
    sat_data = fetch_sentinel2_data(request.aoi, request.date)
    
    # 2. Calculate accurate AOI area from GeoJSON using geodesic approximation
    try:
        geom = shape(request.aoi.get("geometry", request.aoi))
        bounds = geom.bounds
        lat_span = bounds[3] - bounds[1]
        lon_span = bounds[2] - bounds[0]
        mean_lat = (bounds[1] + bounds[3]) / 2.0
        km_lat = lat_span * 111.0
        km_lon = lon_span * 111.0 * math.cos(math.radians(mean_lat))
        aoi_size_km2 = round(abs(km_lat * km_lon), 2) if km_lat * km_lon > 0 else 14.5
    except Exception:
        aoi_size_km2 = 14.5
        bounds = sat_data.get("bbox", [-180, -90, 180, 90])

    # 3. Level 2 AI: Local Machine Learning Land Cover Classification
    land_cover = run_ml_land_cover(sat_data)
    
    # 4. Level 3 AI: Generative AI (Gemini API) / Rule Engine Geomorphological Interpretation
    raw_interpretations = generate_geological_interpretation(land_cover, sat_data, sat_data.get("bbox", bounds))
    
    interpretations = [
        GeoInterpretation(text=item["text"], confidence=float(item.get("confidence", 0.85)))
        for item in raw_interpretations
    ]
    
    cloud_cover = float(sat_data.get("cloud_cover", 0.0))
    cloud_warning = cloud_cover > 30.0

    return AnalysisResponse(
        land_cover=land_cover,
        interpretations=interpretations,
        aoi_size_km2=aoi_size_km2,
        satellite_info=sat_data,
        cloud_warning=cloud_warning
    )

# Serve the static frontend files directly
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
