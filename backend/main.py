import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import math
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from shapely.geometry import shape
from backend.services.satellite import fetch_sentinel2_data
from backend.services.engine import (
    run_ml_land_cover,
    generate_geological_interpretation,
    get_regional_context,
    generate_imagery_overlays
)
from backend.services.literature import fetch_regional_literature

app = FastAPI(title="GeoSentinel AI API", description="AI-powered Geological & Remote Sensing Intelligence Platform")

class AnalysisRequest(BaseModel):
    aoi: Dict[str, Any]
    date: str

class GeoInterpretation(BaseModel):
    text: str
    confidence: float

class ResearchPaper(BaseModel):
    title: str
    authors: List[str] = []
    year: Optional[int] = None
    venue: Optional[str] = None
    doi_url: Optional[str] = None
    is_open_access: bool = False
    oa_url: Optional[str] = None

class AnalysisResponse(BaseModel):
    land_cover: Dict[str, float]
    interpretations: List[GeoInterpretation]
    aoi_size_km2: float
    satellite_info: Dict[str, Any]
    cloud_warning: bool = False
    literature: List[ResearchPaper] = []
    rgb_image: Optional[str] = None
    ndvi_image: Optional[str] = None
    image_bounds: Optional[List[List[float]]] = None

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
    effective_bbox = sat_data.get("bbox", bounds)
    raw_interpretations = generate_geological_interpretation(land_cover, sat_data, effective_bbox)
    
    interpretations = [
        GeoInterpretation(text=item["text"], confidence=float(item.get("confidence", 0.85)))
        for item in raw_interpretations
    ]
    
    # 5. Peer-Reviewed Geological Literature (OpenAlex)
    regional_context = get_regional_context(effective_bbox)
    papers_data = fetch_regional_literature(regional_context, limit=4)
    literature = [ResearchPaper(**p) for p in papers_data]
    
    # 6. Generate True-Color RGB and False-Color NDVI raster overlays
    overlays = generate_imagery_overlays(sat_data, effective_bbox)
    
    cloud_cover = float(sat_data.get("cloud_cover", 0.0))
    cloud_warning = cloud_cover > 30.0
    client_sat_info = {k: v for k, v in sat_data.items() if k != "bands"}

    return AnalysisResponse(
        land_cover=land_cover,
        interpretations=interpretations,
        aoi_size_km2=aoi_size_km2,
        satellite_info=client_sat_info,
        cloud_warning=cloud_warning,
        literature=literature,
        rgb_image=overlays.get("rgb_image"),
        ndvi_image=overlays.get("ndvi_image"),
        image_bounds=overlays.get("image_bounds")
    )

# Serve the static frontend files directly
app.mount("/", StaticFiles(directory=str(ROOT_DIR / "frontend"), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
