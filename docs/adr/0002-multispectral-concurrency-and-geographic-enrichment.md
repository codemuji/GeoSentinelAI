# Multispectral Concurrency, Cloud Warning, and Geographic Enrichment

## Context
Fetching 4 multispectral bands sequentially introduces unacceptable latency (~3.5s). Additionally, cloud interference in remote mountainous areas often obscures surface features, and raw coordinates alone lack the regional context required for high-fidelity geological reasoning.

## Decision
1. Stream Sentinel-2 bands (B03, B04, B08, B11) concurrently using a `ThreadPoolExecutor` within FastAPI.
2. Search scenes within target date ±30 days, selecting the lowest cloud cover; if >30%, flag a `cloud_warning` rather than aborting.
3. Enrich geological prompts with reverse-geocoded regional descriptors (e.g., Eastern Himalayas, Brahmaputra Basin) to ground AI geomorphological interpretation.
4. Update the Leaflet AOI with thematic dominant land cover styling upon analysis completion.

## Consequences
Reduces end-to-end analysis latency to ~1 second, prevents empty/failed responses in cloudy areas, and grounds geological interpretations in regional Earth sciences.
