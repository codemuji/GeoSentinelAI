# 03: Deterministic Multispectral Land Cover Engine

**What to build:** Process streamed multi-band raster arrays using remote sensing spectral physics to compute authentic NDVI, NDWI, and NDBI indices, classifying each pixel within the Area of Interest into Forest, Agriculture, Water, Bare Soil, and Urban classes and delivering accurate percentage distributions through the API.

**Blocked by:** 02: STAC Ingestion with Dynamic CRS Reprojection and Windowed COG Streaming

**Status:** ready-for-agent

- [ ] Compute Normalized Difference Vegetation Index (NDVI) from Near-Infrared and Red bands.
- [ ] Compute Normalized Difference Water Index (NDWI) from Green and Near-Infrared bands.
- [ ] Compute Normalized Difference Built-Up Index (NDBI) from Shortwave-Infrared and Near-Infrared bands.
- [ ] Apply deterministic spectral thresholding rules across all valid pixels to classify them into Forest, Agriculture, Water, Bare Soil, and Urban.
- [ ] Calculate class percentage distributions summing to 100% and wire them directly into the `/api/analyze` response.
- [ ] Verify classification accuracy across synthetic pure water, dense forest, and urban test fixtures.
