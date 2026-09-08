import pytest
from backend.services.literature import (
    build_literature_query,
    format_paper_item,
    fetch_regional_literature
)

def test_build_literature_query_regional_context():
    query = build_literature_query("Tawang, Arunachal Pradesh, India")
    assert "Tawang" in query
    assert "geology" in query

def test_build_literature_query_terrain_sector_fallback():
    query = build_literature_query("Terrain Sector (27.58°N, 91.86°E)")
    assert "geology" in query
    assert "remote sensing" in query

def test_format_paper_item():
    mock_work = {
        "id": "W12345",
        "display_name": "Tectonic evolution of Eastern Himalaya",
        "publication_year": 2024,
        "authorships": [
            {"author": {"display_name": "Dr. A"}},
            {"author": {"display_name": "Dr. B"}},
            {"author": {"display_name": "Dr. C"}},
            {"author": {"display_name": "Dr. D"}},
        ],
        "primary_location": {
            "source": {"display_name": "Journal of Structural Geology"},
            "landing_page_url": "https://example.com/paper"
        },
        "doi": "https://doi.org/10.1016/j.jsg.2024.01",
        "open_access": {
            "is_oa": True,
            "oa_url": "https://example.com/paper.pdf"
        }
    }
    formatted = format_paper_item(mock_work)
    assert formatted["title"] == "Tectonic evolution of Eastern Himalaya"
    assert formatted["year"] == 2024
    assert formatted["authors"] == ["Dr. A", "Dr. B", "Dr. C", "et al."]
    assert formatted["venue"] == "Journal of Structural Geology"
    assert formatted["doi_url"] == "https://doi.org/10.1016/j.jsg.2024.01"
    assert formatted["is_open_access"] is True
    assert formatted["oa_url"] == "https://example.com/paper.pdf"

def test_fetch_regional_literature_mocked(monkeypatch):
    import json
    from io import BytesIO

    mock_payload = {
        "results": [
            {"title": "Paper 2018", "publication_year": 2018, "authorships": [], "open_access": {}},
            {"title": "Paper 2025", "publication_year": 2025, "authorships": [], "open_access": {}},
            {"title": "Paper 2021", "publication_year": 2021, "authorships": [], "open_access": {}},
            {"title": "Paper 2023", "publication_year": 2023, "authorships": [], "open_access": {}},
            {"title": "Paper 2019", "publication_year": 2019, "authorships": [], "open_access": {}},
        ]
    }

    class MockResponse:
        def read(self):
            return json.dumps(mock_payload).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=3.5: MockResponse())

    papers = fetch_regional_literature("Tawang, Arunachal Pradesh", limit=4)
    assert len(papers) == 4
    # Must be sorted by publication_year descending (most recent first)
    years = [p["year"] for p in papers]
    assert years == [2025, 2023, 2021, 2019]

def test_fetch_regional_literature_graceful_on_error(monkeypatch):
    def failing_urlopen(*args, **kwargs):
        raise TimeoutError("Connection timed out")

    monkeypatch.setattr("urllib.request.urlopen", failing_urlopen)
    papers = fetch_regional_literature("Some Location", limit=4)
    assert papers == []

def test_fetch_regional_literature_uses_api_key(monkeypatch):
    import json
    captured_requests = []

    class MockResponse:
        def read(self):
            return json.dumps({"results": []}).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    def mock_urlopen(req, timeout=3.5):
        captured_requests.append(req)
        return MockResponse()

    monkeypatch.setenv("OPENALEX_KEY", "test_alex_key_123")
    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    fetch_regional_literature("Tawang", limit=4)
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert "api_key=test_alex_key_123" in req.full_url
    assert req.headers.get("Api-key") == "test_alex_key_123"

