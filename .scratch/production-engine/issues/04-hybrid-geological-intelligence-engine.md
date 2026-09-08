# 04: Hybrid Geological Intelligence with Regional Context and Dynamic Rule Fallback

**What to build:** Enrich geological reasoning with reverse-geocoded regional context (such as known orogenic belts, valleys, or plateaus), prompt Google Gemini with structured JSON schemas to generate 3 geomorphological landscape interpretations with confidence scores, and provide a dynamic rule engine fallback that produces landscape-specific reasoning when offline or unauthenticated.

**Blocked by:** 03: Deterministic Multispectral Land Cover Engine

**Status:** resolved

- [x] Reverse-geocode the centroid of the Area of Interest to retrieve regional and physiographic locality descriptors.
- [x] Synthesize quantitative spectral metrics, land cover distributions, and regional context into a structured Gemini prompt.
- [x] Parse and validate the Gemini JSON response to ensure exactly 3 geological interpretations with valid confidence floats between 0.0 and 1.0.
- [x] Implement a dynamic geomorphological rule engine fallback that generates varied landscape interpretations based on computed land cover ratios when offline or when no API key is provided.
- [x] Ensure the `/api/analyze` endpoint seamlessly returns valid interpretations in both online (LLM) and offline (rule engine) modes.
