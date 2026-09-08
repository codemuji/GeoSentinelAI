// Initialize Leaflet Map centered on a default area (e.g. Himalayas / Tawang region)
const map = L.map('map', {
  zoomControl: false
}).setView([27.585, 91.859], 9);

// Define Basemaps
const basemaps = {
  dark: L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    maxZoom: 19
  }),
  satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: '&copy; Esri &mdash; Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP',
    maxZoom: 19
  }),
  voyager: L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    maxZoom: 19
  })
};

// Set default basemap
let currentBasemap = basemaps.dark;
currentBasemap.addTo(map);

// Basemap selector handler
document.getElementById('basemap-select').addEventListener('change', (e) => {
  map.removeLayer(currentBasemap);
  currentBasemap = basemaps[e.target.value];
  currentBasemap.addTo(map);
});

// Live Mouse Coordinate Readout (WGS84 Lat/Lng)
map.on('mousemove', (e) => {
  const { lat, lng } = e.latlng;
  document.getElementById('mouse-coords').textContent =
    `Cursor Coordinates: ${Math.abs(lat).toFixed(4)}° ${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lng).toFixed(4)}° ${lng >= 0 ? 'E' : 'W'}`;
});

// Add zoom controls to bottom left
L.control.zoom({ position: 'bottomleft' }).addTo(map);

// Initialize Leaflet Draw FeatureGroup
const drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

const drawControl = new L.Control.Draw({
  position: 'topleft',
  draw: {
    polyline: false,
    circle: false,
    circlemarker: false,
    marker: false,
    polygon: {
      allowIntersection: false,
      shapeOptions: { color: '#00f0ff', weight: 2, fillOpacity: 0.2 }
    },
    rectangle: {
      shapeOptions: { color: '#00f0ff', weight: 2, fillOpacity: 0.2 }
    }
  },
  edit: {
    featureGroup: drawnItems
  }
});
map.addControl(drawControl);

let activeLayer = null;

// Handle AOI Creation
map.on(L.Draw.Event.CREATED, function (e) {
  drawnItems.clearLayers();
  activeLayer = e.layer;
  drawnItems.addLayer(activeLayer);

  const bounds = activeLayer.getBounds();
  const center = bounds.getCenter();

  // Approximate area calculation in sq km
  const areaSqKm = (L.GeometryUtil.geodesicArea(activeLayer.getLatLngs()[0]) / 1000000).toFixed(2);

  document.getElementById('coord-display').textContent = `${center.lat.toFixed(4)}, ${center.lng.toFixed(4)}`;
  document.getElementById('bbox-display').textContent = `${bounds.getSouthWest().lat.toFixed(2)},${bounds.getSouthWest().lng.toFixed(2)} to ${bounds.getNorthEast().lat.toFixed(2)},${bounds.getNorthEast().lng.toFixed(2)}`;
  document.getElementById('area-display').textContent = `${areaSqKm} sq km`;
  document.getElementById('aoi-status').textContent = 'AOI Ready';
  document.getElementById('aoi-status').style.color = 'var(--accent)';

  document.getElementById('analyze-btn').disabled = false;
});

let latestAnalysisData = null;

map.on(L.Draw.Event.DELETED, function () {
  activeLayer = null;
  latestAnalysisData = null;
  document.getElementById('coord-display').textContent = '--';
  document.getElementById('bbox-display').textContent = '--';
  document.getElementById('area-display').textContent = '-- sq km';
  document.getElementById('aoi-status').textContent = 'No AOI Selected';
  document.getElementById('aoi-status').style.color = 'var(--text-secondary)';
  document.getElementById('analyze-btn').disabled = true;
  document.getElementById('report-btn').disabled = true;
  const headerReportBtn = document.getElementById('header-report-btn');
  if (headerReportBtn) headerReportBtn.style.display = 'none';
  const warningBadge = document.getElementById('cloud-warning-badge');
  if (warningBadge) warningBadge.style.display = 'none';
});

// Search functionality using free Nominatim API
document.getElementById('search-btn').addEventListener('click', async () => {
  const query = document.getElementById('location-input').value.trim();
  if (!query) return;

  try {
    const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`);
    const data = await res.json();
    if (data && data.length > 0) {
      const { lat, lon } = data[0];
      map.setView([parseFloat(lat), parseFloat(lon)], 12);
    } else {
      alert('Location not found. Try another place name.');
    }
  } catch (err) {
    console.error('Search error:', err);
  }
});

document.getElementById('location-input').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') document.getElementById('search-btn').click();
});

// Report Modal Controls
function openReportModal() {
  if (!latestAnalysisData) {
    alert('Please draw an Area of Interest on the map and click Analyze AOI first.');
    return;
  }
  populateReportModal(latestAnalysisData);
  const modal = document.getElementById('report-modal');
  if (modal) {
    modal.style.display = 'flex';
    document.body.classList.add('modal-open');
  }
}

function closeReportModal() {
  const modal = document.getElementById('report-modal');
  if (modal) {
    modal.style.display = 'none';
    document.body.classList.remove('modal-open');
  }
}

document.getElementById('report-btn').addEventListener('click', openReportModal);
const headerReportBtn = document.getElementById('header-report-btn');
if (headerReportBtn) headerReportBtn.addEventListener('click', openReportModal);

const modalCloseBtn = document.getElementById('modal-close-btn');
if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeReportModal);

const modalPrintBtn = document.getElementById('modal-print-btn');
if (modalPrintBtn) modalPrintBtn.addEventListener('click', () => {
  window.print();
});

const reportModal = document.getElementById('report-modal');
if (reportModal) {
  reportModal.addEventListener('click', (e) => {
    if (e.target.id === 'report-modal') closeReportModal();
  });
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeReportModal();
});

// Analyze button handler - calls Python FastAPI endpoint
document.getElementById('analyze-btn').addEventListener('click', async () => {
  if (!activeLayer) return;

  const btn = document.getElementById('analyze-btn');
  btn.disabled = true;
  btn.innerHTML = '<span>⏳</span> Analyzing Imagery...';

  const geojson = activeLayer.toGeoJSON();
  const date = document.getElementById('sat-date').value;

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ aoi: geojson, date: date })
    });
    
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Server returned HTTP ${res.status}`);
    }

    const data = await res.json();
    latestAnalysisData = data;
    renderResults(data);

    document.getElementById('report-btn').disabled = false;
    const headerBtn = document.getElementById('header-report-btn');
    if (headerBtn) headerBtn.style.display = 'inline-block';
  } catch (err) {
    console.error('Analysis failed:', err);
    alert(`Analysis failed: ${err.message || 'Make sure the Python server is running!'}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>⚡</span> Analyze AOI';
  }
});

function renderResults(data) {
  // Populate Satellite Metadata
  if (data.satellite_info) {
    document.getElementById('scene-display').textContent = data.satellite_info.scene_id || '--';
    document.getElementById('capture-display').textContent = data.satellite_info.scene_date || '--';
    document.getElementById('cloud-display').textContent = `${data.satellite_info.cloud_cover || 0}%`;
    document.getElementById('ndvi-display').textContent = `${data.satellite_info.ndvi_mean || 0}`;
    document.getElementById('source-display').textContent = data.satellite_info.source || 'Sentinel-2 L2A';
  }

  // Cloud Warning Advisory Badge
  const warningBadge = document.getElementById('cloud-warning-badge');
  if (warningBadge) {
    if (data.cloud_warning) {
      warningBadge.style.display = 'inline-block';
      warningBadge.textContent = `⚠️ Cloud Warning (${data.satellite_info.cloud_cover || 0}%)`;
    } else {
      warningBadge.style.display = 'none';
    }
  }

  const colors = {
    'Forest': '#10b981',
    'Agriculture': '#eab308',
    'Water': '#3b82f6',
    'Bare Soil': '#a855f7',
    'Urban': '#ef4444'
  };

  // Thematic Styling for AOI on Map
  if (data.land_cover && Object.keys(data.land_cover).length > 0) {
    const dominantEntry = Object.entries(data.land_cover).sort((a, b) => b[1] - a[1])[0];
    const dominantClass = dominantEntry[0];
    const dominantColor = colors[dominantClass] || '#00f0ff';

    if (activeLayer && activeLayer.setStyle) {
      activeLayer.setStyle({
        color: dominantColor,
        fillColor: dominantColor,
        fillOpacity: 0.45,
        weight: 3
      });
      activeLayer.bindPopup(
        `<b>Dominant Land Cover:</b> ${dominantClass} (${dominantEntry[1]}%)<br>` +
        `<b>AOI Area:</b> ${data.aoi_size_km2} sq km<br>` +
        `<b>Scene:</b> ${data.satellite_info.scene_id || 'Sentinel-2'}`
      ).openPopup();
    }
  }

  // Render Land Cover Stats
  const statsContainer = document.getElementById('stats-container');
  statsContainer.innerHTML = Object.entries(data.land_cover).map(([cls, pct]) => `
    <div class="stat-item">
      <div class="stat-label">
        <span>${cls}</span>
        <span>${pct}%</span>
      </div>
      <div class="stat-bar">
        <div class="stat-fill" style="width: ${pct}%; background: ${colors[cls] || '#00f0ff'};"></div>
      </div>
    </div>
  `).join('');

  // Render Geological Interpretations
  const geologyContainer = document.getElementById('geology-container');
  geologyContainer.innerHTML = data.interpretations.map(item => `
    <div class="interpretation-item">
      <div>${item.text}</div>
      <div class="confidence">Confidence: ${(item.confidence * 100).toFixed(0)}% • AI-assisted interpretation</div>
    </div>
  `).join('');

  // Render Regional Geological Literature
  const literatureContainer = document.getElementById('literature-container');
  if (literatureContainer) {
    if (data.literature && data.literature.length > 0) {
      literatureContainer.innerHTML = data.literature.map(paper => {
        const authorsText = paper.authors && paper.authors.length > 0 ? paper.authors.join(', ') : 'Unknown authors';
        const yearText = paper.year ? `(${paper.year})` : '';
        const venueText = paper.venue || 'Geological Survey';
        const oaBadge = paper.is_open_access ? '<span class="oa-badge">Open Access</span>' : '';
        const link = paper.doi_url || paper.oa_url || '#';
        const targetAttr = link !== '#' ? 'target="_blank" rel="noopener noreferrer"' : '';

        return `
          <div class="literature-item">
            <a href="${link}" ${targetAttr} class="literature-title">${paper.title} ↗</a>
            <div class="literature-meta">
              <span>${authorsText} ${yearText}</span>
              <span>•</span>
              <span><em>${venueText}</em></span>
              ${oaBadge}
            </div>
          </div>
        `;
      }).join('');
    } else {
      literatureContainer.innerHTML = '<p class="placeholder-text">No indexed geological papers found for this exact geographic sector.</p>';
    }
  }
}

function populateReportModal(data) {
  const timestampEl = document.getElementById('report-timestamp');
  if (timestampEl) {
    timestampEl.textContent = `Mission Date: ${new Date().toLocaleDateString()} | Time: ${new Date().toLocaleTimeString()} (Local)`;
  }

  const sat = data.satellite_info || {};
  const landCover = data.land_cover || {};
  const interpretations = data.interpretations || [];
  const literature = data.literature || [];

  const colors = {
    'Forest': '#10b981',
    'Agriculture': '#eab308',
    'Water': '#3b82f6',
    'Bare Soil': '#a855f7',
    'Urban': '#ef4444'
  };

  const coords = document.getElementById('coord-display')?.textContent || '--';
  const bbox = document.getElementById('bbox-display')?.textContent || '--';
  const area = data.aoi_size_km2 ? `${data.aoi_size_km2} sq km` : (document.getElementById('area-display')?.textContent || '--');

  const distBars = Object.entries(landCover).map(([cls, pct]) => `
    <div class="report-distribution-seg" style="width: ${pct}%; background: ${colors[cls] || '#00f0ff'};" title="${cls}: ${pct}%"></div>
  `).join('');

  const distLegend = Object.entries(landCover).map(([cls, pct]) => `
    <div class="report-legend-item">
      <span class="report-legend-dot" style="background: ${colors[cls] || '#00f0ff'};"></span>
      <span>${cls}: <strong>${pct}%</strong></span>
    </div>
  `).join('');

  const interpHtml = interpretations.length > 0 ? interpretations.map(item => `
    <div class="report-callout">
      <div>${item.text}</div>
      <div class="confidence" style="margin-top:0.3rem;">Confidence: ${(item.confidence * 100).toFixed(0)}% • AI Remote Sensing & Geomorphological Synthesis</div>
    </div>
  `).join('') : '<p class="placeholder-text">No interpretations available.</p>';

  const litHtml = literature.length > 0 ? literature.map(paper => {
    const authors = paper.authors && paper.authors.length > 0 ? paper.authors.join(', ') : 'Unknown Authors';
    const year = paper.year ? `(${paper.year})` : '';
    const venue = paper.venue || 'Academic Geological Publication';
    const oaBadge = paper.is_open_access ? '<span class="oa-badge">Open Access</span>' : '';
    const link = paper.doi_url || paper.oa_url || '#';
    const target = link !== '#' ? 'target="_blank" rel="noopener noreferrer"' : '';

    return `
      <div class="literature-item">
        <a href="${link}" ${target} class="literature-title">${paper.title} ↗</a>
        <div class="literature-meta">
          <span>${authors} ${year}</span>
          <span>•</span>
          <span><em>${venue}</em></span>
          ${oaBadge}
        </div>
      </div>
    `;
  }).join('') : '<p class="placeholder-text">No indexed geological papers found for this sector.</p>';

  const reportBody = document.getElementById('report-body');
  if (reportBody) {
    reportBody.innerHTML = `
      <div class="report-section">
        <h3>1. Mission & Area Specification</h3>
        <div class="report-grid-2">
          <div><label>Centroid Coordinates:</label> <span>${coords}</span></div>
          <div><label>AOI Surface Area:</label> <span>${area}</span></div>
          <div><label>Bounding Box (WGS84):</label> <span>${bbox}</span></div>
          <div><label>Imagery Platform:</label> <span>${sat.source || 'Sentinel-2 L2A'}</span></div>
          <div><label>Acquisition Tile ID:</label> <span style="font-family:monospace; color:var(--accent);">${sat.scene_id || '--'}</span></div>
          <div><label>Acquisition Date:</label> <span>${sat.scene_date || '--'}</span></div>
          <div><label>Cloud / Atmospheric Cover:</label> <span>${sat.cloud_cover || 0}%</span></div>
          <div><label>Mean Spectral NDVI:</label> <span>${sat.ndvi_mean || '--'}</span></div>
        </div>
      </div>

      <div class="report-section">
        <h3>2. Biophysical Land Cover Distribution</h3>
        <div class="report-distribution-bar">
          ${distBars}
        </div>
        <div class="report-legend">
          ${distLegend}
        </div>
      </div>

      <div class="report-section">
        <h3>3. Geomorphological & Structural Landscape Assessment</h3>
        ${interpHtml}
      </div>

      <div class="report-section">
        <h3>4. Ground-Truth Academic Research & Field Surveys (OpenAlex)</h3>
        ${litHtml}
      </div>

      <div class="report-footer-notice">
        GeoSentinel AI Tactical Platform • Sentinel-2 L2A BOA Multispectral Analytics • Microsoft Planetary Computer STAC
      </div>
    `;
  }
}
