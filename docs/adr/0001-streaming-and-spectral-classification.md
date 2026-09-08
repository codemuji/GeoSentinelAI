# Windowed COG Streaming and Spectral Land Cover Classification

## Context
The prototype previously relied on full-scene raster downloads that failed due to CRS projection mismatches between Leaflet WGS84 and Sentinel-2 UTM tiles, falling back to simulated random Gaussian distributions.

## Decision
We stream only bounding-box raster pixels on demand from Microsoft Planetary Computer signed Cloud Optimized GeoTIFF (COG) URLs using `rasterio` and `pyproj` for on-the-fly coordinate reprojection. Land cover is classified using deterministic multispectral index thresholds (NDVI, NDWI, NDBI) computed concurrently across Sentinel-2 bands (B03, B04, B08, B11).

## Consequences
Eliminates multi-gigabyte scene downloads, removes heavy ML dependencies (scikit-learn), and guarantees sub-second, mathematically grounded remote sensing classifications for any coordinate globally.
