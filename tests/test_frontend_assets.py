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
    assert "literature-container" in js

def test_frontend_contains_literature_elements():
    """Verifies that index.html and style.css include literature card and badges."""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    assert "literature-card" in html
    assert "literature-container" in html

    with open("frontend/style.css", "r", encoding="utf-8") as f:
        css = f.read()
    assert ".literature-item" in css
    assert ".oa-badge" in css

def test_frontend_contains_report_modal():
    """Verifies that index.html, app.js, and style.css support the GEOINT report modal."""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    assert "report-modal" in html
    assert "header-report-btn" in html

    with open("frontend/app.js", "r", encoding="utf-8") as f:
        js = f.read()
    assert "openReportModal" in js
    assert "populateReportModal" in js

    with open("frontend/style.css", "r", encoding="utf-8") as f:
        css = f.read()
    assert ".modal-overlay" in css
    assert "body.modal-open" in css

def test_frontend_contains_imagery_viewer_and_stepper():
    """Verifies that index.html, app.js, and style.css support the imagery viewer and progressive stepper."""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    assert "imagery-toolbar" in html
    assert "pipeline-stepper" in html
    assert "imagery-card" in html

    with open("frontend/app.js", "r", encoding="utf-8") as f:
        js = f.read()
    assert "setupRasterOverlays" in js
    assert "setRasterDisplayMode" in js
    assert "runStepperAnimation" in js

    with open("frontend/style.css", "r", encoding="utf-8") as f:
        css = f.read()
    assert ".map-imagery-toolbar" in css
    assert ".pipeline-stepper-overlay" in css
    assert ".imagery-card" in css

