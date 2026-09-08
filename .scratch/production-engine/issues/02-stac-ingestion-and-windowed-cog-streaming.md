# 02: STAC Ingestion with Dynamic CRS Reprojection and Windowed COG Streaming

**What to build:** Enable the platform to search Microsoft Planetary Computer STAC for real Sentinel-2 L2A acquisitions within a ±30-day temporal window around the user-selected date, filter for low cloud cover, dynamically reproject user WGS84 coordinates into the scene''s native UTM coordinate system, and stream Green, Red, Near-Infrared, and Shortwave-Infrared band windows concurrently via HTTP range requests.

**Blocked by:** 01: Dependency Modernization and Offline Test Harness

**Status:** resolved

- [x] Query Planetary Computer STAC for Sentinel-2 L2A scenes intersecting the drawn Area of Interest within a ±30-day window around the selected date.
- [x] Filter scenes by cloud cover to select the cleanest available acquisition, and flag a `cloud_warning: true` indicator when cloud cover exceeds 30%.
- [x] Dynamically reproject the GeoJSON WGS84 bounding box coordinates into the native UTM coordinate reference system of the targeted Sentinel-2 scene.
- [x] Stream only the clipped pixel window using HTTP range requests concurrently across Green (B03), Red (B04), NIR (B08), and SWIR (B11) bands via a thread pool.
- [x] Gracefully handle catalog or network exceptions with informative error responses rather than unhandled server crashes.
