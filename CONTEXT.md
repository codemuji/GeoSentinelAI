# GeoSentinel AI

An Earth Observation intelligence platform that enables interactive surface analysis, multispectral land cover classification, and AI-assisted geological interpretation from satellite imagery.

## Language

**Area of Interest (AOI)**:
The geographic vector boundary drawn by the user on the map defining the target analysis zone.
_Avoid_: ROI, selection polygon, bounding box

**Sentinel-2 L2A**:
Bottom-Of-Atmosphere (BOA) reflectance multispectral satellite imagery acquired by ESA's Sentinel-2 constellation.
_Avoid_: Raw satellite photo, raster download

**Spectral Index**:
A mathematical combination of spectral reflectance bands designed to isolate specific surface characteristics (e.g., NDVI for vegetation, NDWI for water, NDBI for built-up structures).
_Avoid_: Color filter, band math formula

**Land Cover**:
The observed biophysical surface material covering the Earth within an AOI (categorized into Forest, Agriculture, Water, Bare Soil, and Urban).
_Avoid_: Land use, terrain type

**Geological Interpretation**:
A qualitative landscape inference describing geomorphology, bedrock exposure, weathering, and drainage structures derived from remote sensing data.
_Avoid_: Geological prediction, AI chat response, automated diagnosis

**Scene**:
A single acquisition tile of Sentinel-2 satellite imagery covering a specific geographic footprint at a specific timestamp.
_Avoid_: Photo, image, snapshot

**Cloud Warning**:
An advisory flag indicating that atmospheric cloud or shadow cover in the selected scene exceeds optimal thresholds (>30%), potentially reducing spectral accuracy.
_Avoid_: Weather error, image obscured

**Regional Context**:
Geographic and physiographic locality data (e.g., orogenic belts, river basins, administrative districts) associated with an AOI.
_Avoid_: Address, geocode text

**Regional Literature**:
Peer-reviewed academic research papers and geological surveys indexed by OpenAlex associated with the regional context of an AOI.
_Avoid_: Web search results, blog posts, news articles
