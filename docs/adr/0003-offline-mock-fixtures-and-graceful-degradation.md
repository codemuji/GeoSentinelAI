# Offline Mock Fixtures and Graceful Environment Degradation

## Context
Third-party geospatial APIs and LLM services introduce latency, network flakiness, and credential barriers during automated test execution and local development.

## Decision
1. Architect test suites with synthetic 4-band raster fixtures and mock STAC responses, enabling sub-second 100% offline unit/integration test runs (`pytest`). Live network tests are isolated under an integration marker.
2. Load configuration via `.env` with graceful degradation: operate anonymously on Planetary Computer STAC without requiring subscription keys, and fallback to a dynamic geomorphological rule engine when `GEMINI_API_KEY` is not provided.

## Consequences
Tests are deterministic and fast, local development requires zero external account setup, and optional production credentials automatically enhance capabilities without code changes.
