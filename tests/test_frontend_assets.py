from starlette.testclient import TestClient
from backend.main import app
import re

client = TestClient(app)

def test_serves_frontend_index_html():
    """Verifies that root URL mounts and serves index.html."""
    response = client.get("/")
    assert response.status_code == 200
    assert "GeoSentinel" in response.text
    assert "report-btn" in response.text

def test_print_stylesheet_configured():
    """Verifies that style.css contains a dedicated @media print block for PDF export."""
    with open("frontend/style.css", "r", encoding="utf-8") as f:
        css = f.read()
    assert "@media print" in css
    assert "window.print" not in css # sanity check

def test_frontend_script_contains_print_and_thematic_styling():
    """Verifies that app.js wires window.print and dynamic polygon styling."""
    with open("frontend/app.js", "r", encoding="utf-8") as f:
        js = f.read()
    assert "window.print" in js
    assert "cloud_warning" in js
    assert "dominantClass" in js or "dominant" in js
