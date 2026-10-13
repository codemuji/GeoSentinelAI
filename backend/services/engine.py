import os
import json
import io
import base64
from PIL import Image
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
    min_rows = min(bands[b].shape[0] for b in ["B03", "B04", "B08"] if b in bands)
    min_cols = min(bands[b].shape[1] for b in ["B03", "B04", "B08"] if b in bands)

    green = bands["B03"][:min_rows, :min_cols].astype(np.float32)
    red = bands["B04"][:min_rows, :min_cols].astype(np.float32)
    nir = bands["B08"][:min_rows, :min_cols].astype(np.float32)
    swir = bands.get("B11", red)[:min_rows, :min_cols].astype(np.float32)

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
    red = bands["B04"][:ndvi.shape[0], :ndvi.shape[1]]
    nir = bands["B08"][:ndvi.shape[0], :ndvi.shape[1]]

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



def get_regional_context(bbox: List[float]) -> str:
    """
    Reverse-geocodes the centroid of the AOI to obtain physiographic and regional descriptors.
    Falls back to coordinate bounds heuristics when offline.
    """
    lat = (bbox[1] + bbox[3]) / 2.0
    lon = (bbox[0] + bbox[2]) / 2.0
    
    try:
        import urllib.request
        url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}"
        req = urllib.request.Request(url, headers={"User-Agent": "GeoSentinelAI/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as response:
            data = json.loads(response.read().decode())
            addr = data.get("address", {})
            parts = [addr.get("county"), addr.get("state"), addr.get("country")]
            valid_parts = [p for p in parts if p]
            if valid_parts:
                return ", ".join(valid_parts)
    except Exception:
        pass

    # Indian Coastal & Marine Mariculture Belts (ClimaCrew Aquaculture Hubs)
    if 8.5 <= lat <= 10.5 and 78.5 <= lon <= 80.2:
        return "Palk Strait & Gulf of Mannar Marine Biosphere (Tamil Nadu)"
    elif 21.5 <= lat <= 23.5 and 68.5 <= lon <= 70.8:
        return "Gulf of Kutch Coastal Marine Ecosystem (Gujarat)"
    elif 15.5 <= lat <= 16.5 and 73.0 <= lon <= 73.8:
        return "Malvan Marine Sanctuary & Konkan Littoral Shelf (Maharashtra)"
    elif 6.5 <= lat <= 14.0 and 92.0 <= lon <= 94.0:
        return "Andaman & Nicobar Archipelago Marine Ecoregion"
    # Heuristic regional classification based on physiographic bounds
    elif 26.0 <= lat <= 36.0 and 73.0 <= lon <= 98.0:
        return "Eastern Himalayas & Tibetan Orogenic Belt"
    elif 8.0 <= lat <= 21.0 and 73.0 <= lon <= 77.5:
        return "Western Ghats Escarpment"
    elif 15.0 <= lat <= 25.0 and 73.0 <= lon <= 85.0:
        return "Deccan Traps Continental Flood Basalt Plateau"
    elif 23.0 <= lat <= 30.0 and 75.0 <= lon <= 90.0:
        return "Indo-Gangetic Alluvial Foreland Basin"
    else:
        lat_dir = "N" if lat >= 0 else "S"
        lon_dir = "E" if lon >= 0 else "W"
        return f"Terrain Sector ({abs(lat):.2f}°{lat_dir}, {abs(lon):.2f}°{lon_dir})"

def generate_dynamic_geomorphology_rules(
    land_cover: Dict[str, float],
    sat_data: Dict[str, Any],
    regional_context: str
) -> List[Dict[str, Any]]:
    """
    Dynamic Geomorphological Rule Engine.
    Synthesizes bedrock exposure, surface weathering, and drainage pattern reasoning
    based on computed multispectral ratios and regional physiography.
    """
    ndvi = float(sat_data.get("ndvi_mean", 0.35))
    bare = float(land_cover.get("Bare Soil", 0.0))
    forest = float(land_cover.get("Forest", 0.0))
    water = float(land_cover.get("Water", 0.0))
    agri = float(land_cover.get("Agriculture", 0.0))
    urban = float(land_cover.get("Urban", 0.0))

    # Statement 1: Bedrock, Lithology, or Coastal Marine Photic Zone
    is_marine_context = any(m in regional_context.lower() for m in ["marine", "gulf", "strait", "coast", "littoral", "archipelago", "bay"])
    if is_marine_context or water > 35.0:
        interp_1 = (
            f"Littoral shelf bathymetry across {regional_context} provides a stable coastal photic zone "
            f"conducive to benthic macroalgae colonization and seaweed aquaculture."
        )
        conf_1 = 0.89
        interp_2 = (
            f"Surface hydrodynamic kinetics and tidal wave attenuation across {water:.1f}% marine surface reflect "
            f"sheltered coastal embayment conditions optimal for monoline/raft mariculture."
        )
        conf_2 = 0.86
        interp_3 = (
            f"Low terrigenous sediment influx and moderate optical clarity support sustained carbon sequestration "
            f"and high-yield Kappaphycus alvarezii / Gracilaria biomass growth."
        )
        conf_3 = 0.83
        return [
            {"text": interp_1, "confidence": conf_1},
            {"text": interp_2, "confidence": conf_2},
            {"text": interp_3, "confidence": conf_3}
        ]

    if bare > 40.0:
        interp_1 = (
            f"Widespread exposed barren surface ({bare:.1f}%) in {regional_context} indicates active mechanical "
            f"weathering and prominent bedrock exposure with minimal regolith development."
        )
        conf_1 = 0.88
    elif forest > 50.0:
        interp_1 = (
            f"Dense vegetative canopy (NDVI {ndvi:.2f}, {forest:.1f}% forest) across {regional_context} strongly "
            f"obscures underlying bedrock lithology and structural fracture lines."
        )
        conf_1 = 0.85
    elif urban > 30.0:
        interp_1 = (
            f"High urban built-up density ({urban:.1f}%) has substantially modified natural topography and "
            f"engineered slope morphology across {regional_context}."
        )
        conf_1 = 0.82
    else:
        interp_1 = (
            f"Mixed agricultural and vegetative cover ({agri + forest:.1f}%) in {regional_context} reflects "
            f"moderately developed soil horizons overlying consolidated strata."
        )
        conf_1 = 0.80

    # Statement 2: Fluvial / Surface processes
    if water > 20.0:
        interp_2 = (
            f"Significant surface water presence ({water:.1f}%) suggests active fluvial dynamics, alluvial floodplain "
            f"deposition, and structural river channel meandering."
        )
        conf_2 = 0.86
    elif bare > 30.0:
        interp_2 = (
            f"Exposed slopes and barren margins ({bare:.1f}%) indicate susceptibility to mass wasting, slope wash, "
            f"and high-energy gravitational sediment transport."
        )
        conf_2 = 0.83
    else:
        interp_2 = (
            f"Surface weathering and erosional processes are mediated by root binding across {forest + agri:.1f}% "
            f"vegetative mantle, stabilizing steep gradient slopes."
        )
        conf_2 = 0.79

    # Statement 3: Structural & Drainage pattern
    if water > 10.0:
        interp_3 = (
            f"Linear drainage corridors adjacent to open water ({water:.1f}%) exhibit structural control along fault "
            f"zones or joint-aligned valley systems."
        )
        conf_3 = 0.81
    elif bare > 25.0:
        interp_3 = (
            f"Exposed crests and lineaments indicate differential weathering along resistant lithological units "
            f"within {regional_context}."
        )
        conf_3 = 0.77
    else:
        interp_3 = (
            f"Sub-dendritic drainage networks reflect homogeneous substrate resistance under humid sub-tropical to "
            f"montane climate regimes."
        )
        conf_3 = 0.76

    return [
        {"text": interp_1, "confidence": conf_1},
        {"text": interp_2, "confidence": conf_2},
        {"text": interp_3, "confidence": conf_3}
    ]

def generate_geological_interpretation(
    land_cover: Dict[str, float],
    sat_data: Dict[str, Any],
    bbox: List[float]
) -> List[Dict[str, Any]]:
    """
    Hybrid Geological Intelligence Engine.
    Uses Gemini when GEMINI_API_KEY is configured with structured JSON schema,
    falling back to the dynamic geomorphology rule engine when offline or unauthenticated.
    """
    regional_context = get_regional_context(bbox)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    if GENAI_AVAILABLE and api_key:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""You are a Senior Exploration Geologist and Remote Sensing Scientist.
Analyze the following Earth Observation data for the selected Area of Interest (AOI):
- Regional Physiographic Context: {regional_context}
- Bounding Box (WGS84): {bbox}
- Satellite Source: {sat_data.get('source')} (Date: {sat_data.get('scene_date')})
- Mean Spectral NDVI: {sat_data.get('ndvi_mean')}
- Land Cover Classification: {json.dumps(land_cover)}

Based on these exact quantitative remote sensing metrics and the geographic regional context, output exactly 3 professional geological, geomorphological, or structural landscape interpretations.
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
            if isinstance(parsed, list) and len(parsed) >= 3:
                return [
                    {
                        "text": str(item["text"]),
                        "confidence": min(1.0, max(0.0, float(item.get("confidence", 0.85))))
                    }
                    for item in parsed[:3]
                ]
        except Exception as e:
            print(f"[Gemini API Notice] Using Rule Engine fallback: {e}")

    # Fallback: Dynamic Geomorphological Rule Engine
    return generate_dynamic_geomorphology_rules(land_cover, sat_data, regional_context)

def stretch_reflectance_channel(ch: np.ndarray, p_low: float = 2.0, p_high: float = 98.0) -> np.ndarray:
    """Linearly stretches satellite surface reflectance channel to 0-255 uint8 range."""
    valid = ch[ch > 0]
    if valid.size == 0:
        return np.zeros_like(ch, dtype=np.uint8)
    vmin = float(np.percentile(valid, p_low))
    vmax = float(np.percentile(valid, p_high))
    if vmax <= vmin:
        vmax = vmin + 0.15
    stretched = np.clip((ch - vmin) / (vmax - vmin), 0.0, 1.0)
    return (stretched * 255.0).astype(np.uint8)

def encode_pil_png_data_url(image: Image.Image) -> str:
    """Encodes a PIL Image into a base64 PNG data URL."""
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

def create_synthetic_terrain_bands(bbox: List[float], ndvi_mean: float = 0.38) -> Dict[str, np.ndarray]:
    """Generates synthetic 64x64 spectral band arrays for simulated offline rendering."""
    x = np.linspace(0, 3 * np.pi, 64)
    y = np.linspace(0, 3 * np.pi, 64)
    xx, yy = np.meshgrid(x, y)
    
    lat = (bbox[1] + bbox[3]) / 2.0
    lon = (bbox[0] + bbox[2]) / 2.0
    is_marine = ndvi_mean < 0.20 or (8.0 <= lat <= 11.0 and 78.0 <= lon <= 80.5) or (21.5 <= lat <= 23.5 and 68.5 <= lon <= 71.0)

    if is_marine:
        # Coastal marine water with nearshore reef / macroalgal patch
        water_depth = np.clip(0.5 + 0.4 * np.sin(xx * 0.6 + yy * 0.4), 0.1, 0.9).astype(np.float32)
        b02_blue = np.clip(0.16 + 0.08 * (1.0 - water_depth), 0.10, 0.30).astype(np.float32)
        b03_green = np.clip(0.11 + 0.06 * (1.0 - water_depth), 0.06, 0.24).astype(np.float32)
        b04_red = np.clip(0.04 + 0.03 * (1.0 - water_depth), 0.02, 0.14).astype(np.float32)
        # Macroalgal rafts in protected shallows show sharp NIR signature
        algae_patch = np.exp(-((xx - 4.5)**2 + (yy - 4.5)**2) / 4.0).astype(np.float32)
        b08_nir = np.clip(0.02 + 0.28 * algae_patch, 0.01, 0.45).astype(np.float32)
        b11_swir = np.clip(0.015 + 0.06 * algae_patch, 0.01, 0.20).astype(np.float32)
        return {"B02": b02_blue, "B03": b03_green, "B04": b04_red, "B08": b08_nir, "B11": b11_swir}

    # Terrestrial vegetation gradient modulated by elevation & target mean
    veg_factor = np.clip(ndvi_mean + 0.2 * np.sin(xx * 0.8), 0.05, 0.85).astype(np.float32)
    b04_red = np.clip(0.18 * (1.0 - veg_factor) + 0.04, 0.02, 0.35).astype(np.float32)
    b03_green = np.clip(0.12 * veg_factor + 0.05, 0.03, 0.30).astype(np.float32)
    b02_blue = np.clip(b03_green * 0.75 + 0.02, 0.02, 0.25).astype(np.float32)
    b08_nir = np.clip(b04_red + veg_factor * 0.45, 0.05, 0.65).astype(np.float32)
    b11_swir = np.clip(b04_red * 0.9, 0.02, 0.40).astype(np.float32)
    
    return {"B02": b02_blue, "B03": b03_green, "B04": b04_red, "B08": b08_nir, "B11": b11_swir}

def generate_imagery_overlays(sat_data: Dict[str, Any], bbox: List[float]) -> Dict[str, Any]:
    """
    Generates True-Color (RGB), False-Color NDVI, and Floating Algae Index (FAI) PNG data URLs
    for AOI map overlays formatted for Leaflet L.imageOverlay.
    """
    bands = sat_data.get("bands", {})
    required = ["B03", "B04", "B08"]
    has_real_bands = all(b in bands and isinstance(bands[b], np.ndarray) and bands[b].size > 0 for b in required)

    if not has_real_bands:
        ndvi_mean = float(sat_data.get("ndvi_mean", 0.38))
        bands = create_synthetic_terrain_bands(bbox, ndvi_mean)

    min_rows = min(bands[b].shape[0] for b in ["B03", "B04", "B08"] if b in bands)
    min_cols = min(bands[b].shape[1] for b in ["B03", "B04", "B08"] if b in bands)

    red = bands["B04"][:min_rows, :min_cols].astype(np.float32)
    green = bands["B03"][:min_rows, :min_cols].astype(np.float32)
    if "B02" in bands and bands["B02"].size > 0:
        blue = bands["B02"][:min_rows, :min_cols].astype(np.float32)
    else:
        blue = (green * 0.82).astype(np.float32)
    nir = bands["B08"][:min_rows, :min_cols].astype(np.float32)
    swir = bands.get("B11", red * 0.75)[:min_rows, :min_cols].astype(np.float32)

    # 1. True-Color RGB Image
    r_uint8 = stretch_reflectance_channel(red)
    g_uint8 = stretch_reflectance_channel(green)
    b_uint8 = stretch_reflectance_channel(blue)
    rgb_arr = np.dstack([r_uint8, g_uint8, b_uint8])
    rgb_img = Image.fromarray(rgb_arr, mode="RGB")
    
    # Upscale smoothly if raster window is small
    target_dim = max(256, max(min_cols, min_rows))
    if min_cols < target_dim or min_rows < target_dim:
        rgb_img = rgb_img.resize((target_dim, target_dim), Image.Resampling.BILINEAR)

    # 2. Continuous False-Color NDVI Heatmap (RGBA with alpha transparency)
    denom = nir + red + 1e-6
    ndvi = np.clip((nir - red) / denom, -1.0, 1.0)
    
    stops = [-0.2, 0.1, 0.35, 0.6, 0.85]
    colors = [
        [30, 80, 200],    # Deep Navy/Blue (Water)
        [210, 180, 130],  # Tan/Sand (Bare Soil / Rock)
        [230, 210, 60],   # Yellow/Olive (Sparse Vegetation)
        [70, 180, 60],    # Vibrant Green (Moderate Vegetation)
        [15, 110, 30]     # Rich Emerald (Dense Canopy)
    ]
    ndvi_r = np.interp(ndvi, stops, [c[0] for c in colors]).astype(np.uint8)
    ndvi_g = np.interp(ndvi, stops, [c[1] for c in colors]).astype(np.uint8)
    ndvi_b = np.interp(ndvi, stops, [c[2] for c in colors]).astype(np.uint8)
    ndvi_a = np.full_like(ndvi_r, 220, dtype=np.uint8)
    
    ndvi_rgba = np.dstack([ndvi_r, ndvi_g, ndvi_b, ndvi_a])
    ndvi_img = Image.fromarray(ndvi_rgba, mode="RGBA")
    if min_cols < target_dim or min_rows < target_dim:
        ndvi_img = ndvi_img.resize((target_dim, target_dim), Image.Resampling.BILINEAR)

    # 3. Floating Algal Index (FAI / Macroalgae Seaweed Canopy Heatmap)
    # FAI = NIR - [Red + (SWIR - Red) * ((842 - 665) / (1610 - 665))] = NIR - [Red + (SWIR - Red) * 0.1873]
    fai_baseline = red + (swir - red) * 0.1873
    fai = nir - fai_baseline

    fai_stops = [-0.04, -0.01, 0.01, 0.035, 0.075]
    fai_colors = [
        [6, 24, 52],      # Abyssal Navy (Deep Clear Marine Water)
        [0, 150, 180],    # Marine Turquoise (Coastal Photic Ocean)
        [20, 205, 140],   # Aquamarine (Algal Productivity / Phytoplankton)
        [57, 255, 20],    # Neon Lime Green (Dense Floating Macroalgae / Seaweed Rafts)
        [255, 220, 0]     # Luminous Gold (Harvest-Ready Macroalgae Canopy)
    ]
    fai_r = np.interp(fai, fai_stops, [c[0] for c in fai_colors]).astype(np.uint8)
    fai_g = np.interp(fai, fai_stops, [c[1] for c in fai_colors]).astype(np.uint8)
    fai_b = np.interp(fai, fai_stops, [c[2] for c in fai_colors]).astype(np.uint8)
    fai_a = np.full_like(fai_r, 225, dtype=np.uint8)

    # Subdue terrestrial landmass (high NDVI / high NIR) into muted dark slate
    land_mask = (ndvi > 0.28) & (nir > 0.20)
    fai_r[land_mask] = 18
    fai_g[land_mask] = 26
    fai_b[land_mask] = 36
    fai_a[land_mask] = 175

    fai_rgba = np.dstack([fai_r, fai_g, fai_b, fai_a])
    fai_img = Image.fromarray(fai_rgba, mode="RGBA")
    if min_cols < target_dim or min_rows < target_dim:
        fai_img = fai_img.resize((target_dim, target_dim), Image.Resampling.BILINEAR)

    # Image bounds in Leaflet [[South, West], [North, East]] order
    image_bounds = [
        [float(bbox[1]), float(bbox[0])],
        [float(bbox[3]), float(bbox[2])]
    ]

    return {
        "rgb_image": encode_pil_png_data_url(rgb_img),
        "ndvi_image": encode_pil_png_data_url(ndvi_img),
        "fai_image": encode_pil_png_data_url(fai_img),
        "image_bounds": image_bounds
    }

def compute_mariculture_intelligence(
    land_cover: Dict[str, float],
    sat_data: Dict[str, Any],
    aoi_size_km2: float,
    bbox: List[float]
) -> Dict[str, Any]:
    """
    Computes Coastal Seaweed Mariculture Suitability, Marine Indicators,
    and Blue Carbon Sequestration MRV Projections (tailored for ClimaCrew Blue Economy).
    """
    water_pct = float(land_cover.get("Water", 0.0))
    lat = (bbox[1] + bbox[3]) / 2.0
    lon = (bbox[0] + bbox[2]) / 2.0
    
    is_known_marine_zone = (
        (8.0 <= lat <= 11.0 and 78.0 <= lon <= 80.5) or   # Palk Bay & Gulf of Mannar (Tamil Nadu)
        (21.5 <= lat <= 23.5 and 68.5 <= lon <= 71.0) or  # Gulf of Kutch (Gujarat)
        (15.5 <= lat <= 16.5 and 73.0 <= lon <= 73.8) or  # Malvan / Sindhudurg (Maharashtra)
        (6.5 <= lat <= 14.0 and 92.0 <= lon <= 94.0)      # Andaman & Nicobar Archipelago
    )
    
    is_coastal = water_pct >= 2.0 or is_known_marine_zone
    if not is_coastal:
        return {
            "is_coastal": False,
            "suitability_score": 0.0,
            "feasibility_tier": "INLAND // NON-MARINE AOI",
            "recommended_species": [],
            "water_area_ha": 0.0,
            "water_clarity": "N/A",
            "estimated_chlorophyll_mg_m3": 0.0,
            "wet_biomass_annual_tonnes": 0.0,
            "co2_sequestered_t_annual": 0.0,
            "coastal_jobs_supported": 0,
            "summary": "AOI is located in an inland terrestrial biome (<2% water surface). Mariculture analysis is inactive."
        }

    # Effective coastal water area in hectares (1 km2 = 100 hectares)
    effective_water_pct = max(water_pct, 18.0 if is_known_marine_zone else 5.0)
    water_area_ha = round((aoi_size_km2 * 100.0) * (effective_water_pct / 100.0), 1)
    
    # Spectral band heuristics for water clarity
    bands = sat_data.get("bands", {})
    if "B04" in bands and "B03" in bands and isinstance(bands["B04"], np.ndarray):
        b04 = bands["B04"]
        b03 = bands["B03"]
        turbidity_ratio = float(np.mean(b04) / (np.mean(b03) + 1e-6))
    else:
        turbidity_ratio = 0.92

    if turbidity_ratio < 0.88:
        water_clarity = "High Clarity (Clear Marine Water)"
        clarity_score = 92
    elif turbidity_ratio <= 1.15:
        water_clarity = "Moderate Clarity (Nutrient-Rich Coastal)"
        clarity_score = 85
    else:
        water_clarity = "Turbid (Elevated Sediment Influx)"
        clarity_score = 55

    # Chlorophyll-a / Algal proxy (mg/m3)
    ndvi_mean = float(sat_data.get("ndvi_mean", 0.15))
    chla_est = round(max(0.12, min(2.5, 0.35 + (ndvi_mean * 0.8) + (0.1 if is_known_marine_zone else 0.0))), 2)

    # Suitability Scoring (0-100)
    base_score = 78.0
    if is_known_marine_zone:
        base_score += 12.0
    if clarity_score >= 85:
        base_score += 5.0
    else:
        base_score -= 15.0
    cloud_cover = float(sat_data.get("cloud_cover", 0.0))
    if cloud_cover > 20:
        base_score -= 8.0
    suitability_score = round(max(20.0, min(97.0, base_score)), 1)

    if suitability_score >= 82:
        feasibility_tier = "OPTIMAL - TIER 1 (PRIME SEAWEED CORRIDOR)"
    elif suitability_score >= 65:
        feasibility_tier = "VIABLE - TIER 2 (MODERATE HYDRODYNAMIC RISK)"
    else:
        feasibility_tier = "MARGINAL - TIER 3 (ELEVATED TURBIDITY / SEDIMENT PLUME)"

    recommended_species = [
        "Kappaphycus alvarezii (Carrageenan / High-Value Hydrocolloid)",
        "Gracilaria edulis (Agar / Food & Pharmaceutical Grade)",
        "Sargassum wightii (Alginates & Organic Plant Biostimulants)"
    ]

    # Blue Carbon MRV Projections:
    # Industry standard for Indian coastal monoline/bamboo raft farming: ~42-48 wet MT / hectare / year.
    # Dry weight is ~10% of wet weight. Carbon fraction is ~30% of dry weight.
    # CO2 equivalent: Carbon * (44 / 12) = 3.67x carbon weight.
    wet_biomass = round(water_area_ha * 44.5, 1)
    dry_biomass = round(wet_biomass * 0.10, 1)
    c_tonnes = dry_biomass * 0.30
    co2e_annual = round(c_tonnes * (44.0 / 12.0), 2)
    jobs = max(1, int(water_area_ha * 1.4))

    summary = (
        f"Coastal mariculture assessment indicates {suitability_score}% suitability ({feasibility_tier}). "
        f"Evaluated {water_area_ha} ha of marine waters with {water_clarity}. "
        f"Projected annual wet biomass: {wet_biomass:,.1f} MT, sequestering approximately {co2e_annual:,.1f} tCO₂e/yr "
        f"across sustainable raft/monoline deployments, supporting an estimated {jobs} coastal fisherfolk livelihoods."
    )

    return {
        "is_coastal": True,
        "suitability_score": suitability_score,
        "feasibility_tier": feasibility_tier,
        "recommended_species": recommended_species,
        "water_area_ha": water_area_ha,
        "water_clarity": water_clarity,
        "estimated_chlorophyll_mg_m3": chla_est,
        "wet_biomass_annual_tonnes": wet_biomass,
        "co2_sequestered_t_annual": co2e_annual,
        "coastal_jobs_supported": jobs,
        "summary": summary
    }

