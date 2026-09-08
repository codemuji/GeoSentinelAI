# 01: Dependency Modernization and Offline Test Harness

**What to build:** Configure production geospatial and remote sensing dependencies, strip the obsolete in-request machine learning fitting code, and establish an automated test suite capable of running 100% offline in under two seconds with deterministic 4-band raster fixtures to verify the core API contract.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] Unused heavy machine learning dependencies are replaced with production remote sensing packages (`rasterio`, `pyproj`, `pystac-client`, `planetary-computer`, `numpy`, `python-dotenv`, `pytest`, `httpx`).
- [x] Obsolete in-request model fitting routines are purged from the analytical engine.
- [x] An automated test suite is established that runs completely offline without internet or API keys in under 2 seconds.
- [x] Synthetic 4-band raster fixtures (water, dense vegetation, bare soil, urban) are available for deterministic unit and integration tests.
- [x] The `/api/analyze` endpoint contract responds with the expected JSON schema when supplied with a valid GeoJSON Area of Interest.
