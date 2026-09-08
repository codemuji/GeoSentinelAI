Status: ready-for-agent

# Feature: Production Earth Observation Intelligence Engine

## Problem Statement

Users exploring Earth Observation data using GeoSentinel AI currently experience broken workflows and inaccurate results. The previous implementation decoupled the user''s Area of Interest (AOI) from actual satellite imagery due to projection mismatches between browser coordinates (WGS84) and Sentinel-2 UTM tiles, causing the backend to silently fall back to center-cropped thumbnails and hardcoded dummy numbers. Furthermore, land cover classification was faked using random Gaussian noise generated in-request, cloud cover was unhandled, and features like geological insights and PDF reports lacked real-world grounding and functional backing. Users cannot rely on the platform for credible environmental monitoring or geological landscape assessment.

## Solution

Re-engineer GeoSentinel AI into an authentic, production-grade Earth Observation platform. When a user draws an Area of Interest (AOI) and selects a date, the platform queries Planetary Computer STAC for Sentinel-2 L2A imagery within a temporal search window, reprojects the bounding box to the raster''s native UTM coordinate system on the fly, and streams only the requested bounding box pixels over HTTP using concurrent range requests across Green, Red, Near-Infrared, and Shortwave-Infrared bands. The platform computes real spectral indices (NDVI, NDWI, NDBI) to deterministically classify land cover into five biophysical classes. A hybrid geological engine enriches quantitative metrics with regional geographic context to generate structured geological reasoning via Google Gemini, gracefully falling back to a dynamic geomorphology rule engine when offline. Results are dynamically visualized on the interactive map and exportable as professional PDF reports via the browser print system.

## User Stories

1. As a GIS researcher, I want to draw an Area of Interest (AOI) anywhere on the interactive map, so that I can define an exact spatial boundary of interest for analysis.
2. As an environmental analyst, I want to select a target satellite acquisition date, so that I can inspect surface conditions at a specific time of year.
3. As an Earth scientist, I want the system to query Sentinel-2 L2A imagery within a ±30-day temporal window around my chosen date, so that the search reliably finds clear, cloud-free imagery.
4. As an analyst, I want the system to filter scenes by cloud cover and select the cleanest available acquisition, so that my analysis is not corrupted by atmospheric occlusion.
5. As a user, I want to see a prominent Cloud Warning badge if the best available scene still has greater than 30% cloud cover, so that I am aware of potential atmospheric interference in the spectral data.
6. As a researcher, I want the platform to stream only the pixels within my drawn AOI using windowed HTTP range requests without downloading full multi-gigabyte satellite scenes, so that analysis results return in seconds.
7. As a GIS practitioner, I want the backend to automatically reproject my WGS84 GeoJSON geometry into the native UTM coordinate reference system of the Sentinel-2 tile on the fly, so that the analyzed pixels precisely correspond to my drawn boundary.
8. As a remote sensing specialist, I want the system to compute authentic multispectral indices (NDVI for vegetation, NDWI for water, NDBI for built structures) across Green, Red, NIR, and SWIR bands, so that classifications are grounded in verified satellite physics.
9. As an environmental auditor, I want accurate percentage breakdowns for Forest, Agriculture, Water, Bare Soil, and Urban land cover, so that I can evaluate true biophysical distributions within the AOI.
10. As an exploration geologist, I want AI-assisted geological interpretations that describe geomorphology, bedrock exposure, weathering, and drainage patterns, so that I can understand the underlying landscape structure.
11. As a geologist, I want geological interpretations to automatically incorporate regional geographic context (such as known tectonic belts, plateaus, or river basins), so that the reasoning is specifically tailored to the local regional geology.
12. As a developer running the system offline or without external API keys, I want the geological reasoning to gracefully fall back to a dynamic geomorphological rule engine, so that the platform remains 100% operational without configuration friction.
13. As a user viewing completed analysis results, I want the drawn AOI on the map to update dynamically with a thematic color reflecting the dominant land cover class, so that I receive immediate visual feedback directly on the map.
14. As an analyst, I want to view verified scene provenance (Scene ID, capture date, cloud cover percentage, and mean NDVI) in the dashboard, so that I can trace all findings back to the originating satellite acquisition.
15. As a decision maker, I want to click a Download PDF Report button to generate a clean, branded briefing document via the browser print system, so that I can share findings with stakeholders without backend PDF rendering dependencies.
16. As a software engineer, I want all analytical routines and API endpoints covered by fast, 100% offline automated unit tests using synthetic raster fixtures, so that code changes can be verified rapidly and reliably in local environments and CI.

## Implementation Decisions

### Modular Architecture
- **Satellite Ingestion Module**: Interfaces with Planetary Computer STAC using open catalog endpoints. Accepts a WGS84 GeoJSON AOI and date string, queries Sentinel-2 L2A items within a ±30-day window, reprojects spatial bounds into the scene''s native UTM CRS, and executes concurrent HTTP range requests across bands B03, B04, B08, and B11 using a thread pool. (Ref: ADR-0001, ADR-0002).
- **Spectral Land Cover Engine**: Accepts multi-band raster arrays, masks invalid/nodata pixels, computes normalized difference spectral index arrays (NDVI, NDWI, NDBI), applies deterministic thresholding rules to classify pixels into Forest, Agriculture, Water, Bare Soil, and Urban, and computes percentage distributions. (Ref: ADR-0001).
- **Geological Intelligence Engine**: Reverse-geocodes AOI centroids to determine regional locality descriptors. Combines quantitative spectral metrics, land cover distributions, and regional context into a structured prompt for Google Gemini. If API credentials are missing or network calls fail, activates a dynamic geomorphological rule engine that generates varied landscape interpretations based on computed land cover and water/vegetation ratios. (Ref: ADR-0002, ADR-0003).
- **API Boundary & Service Layer**: FastAPI application exposing the `/api/analyze` endpoint. Validates requests via Pydantic models, coordinates ingestion and engines, and returns verified metadata and analysis results. Serves static frontend assets. (Ref: ADR-0001).
- **Interactive Map & Dashboard Client**: Vanilla JavaScript and Leaflet application. Supports drawing polygons and rectangles, provides geocoding search, submits analysis requests, visually updates the AOI polygon with the dominant land cover color, renders statistics and geological cards, displays cloud warnings, and triggers browser print styling for PDF export. (Ref: ADR-0002).

### API Contract (`/api/analyze`)
- **Request Payload**:
  - `aoi`: GeoJSON Feature or Geometry object representing the drawn Area of Interest.
  - `date`: ISO 8601 date string (`YYYY-MM-DD`).
- **Response Payload**:
  - `land_cover`: Object mapping class names (`Forest`, `Agriculture`, `Water`, `Bare Soil`, `Urban`) to percentage floats summing to 100%.
  - `interpretations`: Array of 3 objects containing `text` (string) and `confidence` (float between 0.0 and 1.0).
  - `aoi_size_km2`: Float representing the geodesic area in square kilometers.
  - `satellite_info`: Object containing `scene_id`, `scene_date`, `cloud_cover`, `source`, `ndvi_mean`, and `spectral_stats`.
  - `cloud_warning`: Boolean indicating whether scene cloud cover exceeds 30%.

### Dependency Cleanup & Configuration
- Remove unused heavy machine learning dependencies (`scikit-learn`) and replace them with standard remote sensing and spatial utilities (`rasterio`, `pyproj`, `pystac-client`, `planetary-computer`, `numpy`, `python-dotenv`).
- Load configuration with zero-config graceful degradation: optional `GEMINI_API_KEY` for LLM interpretations, with anonymous STAC access enabled by default. (Ref: ADR-0003).

## Testing Decisions

### Testing Philosophy
- Tests must verify external behavior and system contracts rather than private implementation details.
- All unit and integration tests must run 100% offline in under 2 seconds without external network dependencies or API keys.

### Test Coverage & Seams
- **High-Level Seam (`/api/analyze`)**: Test the complete HTTP pipeline using FastAPI test client. Verify valid GeoJSON processing, correct JSON response structures, error handling for malformed geometries, and fallback behavior when Gemini is unconfigured.
- **Spectral Engine Seam**: Test spectral index computation and land cover thresholding using deterministic synthetic 4-band numpy arrays with known signatures (e.g., pure water fixture, dense canopy fixture, mixed urban fixture).
- **Spatial Transformation Seam**: Verify that WGS84 bounding box coordinates correctly transform into UTM coordinates matching target raster coordinate systems.
- **Geomorphology Rule Seam**: Verify that the dynamic fallback rule engine produces valid, diverse interpretations with valid confidence scores across diverse land cover ratios.

## Out of Scope

- Multi-temporal satellite change detection (comparing two distinct dates).
- Digital Elevation Model (DEM) 3D surface mesh generation or hillshade rendering.
- Heavy server-side PDF compilation engines (e.g., WeasyPrint, ReportLab).
- User account authentication, billing, or database persistence.
- Real-time video or high-resolution commercial imagery providers (Planet, Maxar).

## Further Notes

- All domain terms align strictly with `CONTEXT.md`.
- Architectural choices are tracked in `docs/adr/0001-streaming-and-spectral-classification.md`, `docs/adr/0002-multispectral-concurrency-and-geographic-enrichment.md`, and `docs/adr/0003-offline-mock-fixtures-and-graceful-degradation.md`.
