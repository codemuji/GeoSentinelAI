// Initialize Leaflet Map centered on default area without Leaflet watermark
const map = L.map('map', {
  zoomControl: false,
  attributionControl: false
}).setView([27.585, 91.859], 9);

// Live UTC Telemetry Clock
function updateUtcClock() {
  const clock = document.getElementById('utc-clock');
  if (clock) {
    const now = new Date();
    clock.textContent = `UTC ${now.toISOString().substring(11, 19)}Z`;
  }
}
setInterval(updateUtcClock, 1000);
updateUtcClock();

// Define Basemaps (Reliable ESRI & OSM tiles without API keys or watermarks)
const basemaps = {
  dark: L.layerGroup([
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{x}/{y}', {
      maxZoom: 19,
      maxNativeZoom: 16
    }),
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{x}/{y}', {
      maxZoom: 19,
      maxNativeZoom: 16
    })
  ]),
  satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{x}/{y}', {
    maxZoom: 19
  }),
  topo: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{x}/{y}', {
    maxZoom: 19
  }),
  osm: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
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

// Live Tactical Reticle Coordinate Readout (WGS84 Lat/Lng)
map.on('mousemove', (e) => {
  const { lat, lng } = e.latlng;
  const latStr = `${Math.abs(lat).toFixed(4)}°${lat >= 0 ? 'N' : 'S'}`;
  const lngStr = `${Math.abs(lng).toFixed(4)}°${lng >= 0 ? 'E' : 'W'}`;
  document.getElementById('mouse-coords').textContent =
    `RETICLE // ${latStr} · ${lngStr} | GRID: WGS84`;
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
let rgbOverlayLayer = null;
let ndviOverlayLayer = null;
let faiOverlayLayer = null;
let currentRasterMode = 'rgb';
let currentOpacity = 0.85;

function clearRasterOverlays() {
  if (rgbOverlayLayer && map.hasLayer(rgbOverlayLayer)) map.removeLayer(rgbOverlayLayer);
  if (ndviOverlayLayer && map.hasLayer(ndviOverlayLayer)) map.removeLayer(ndviOverlayLayer);
  if (faiOverlayLayer && map.hasLayer(faiOverlayLayer)) map.removeLayer(faiOverlayLayer);
  rgbOverlayLayer = null;
  ndviOverlayLayer = null;
  faiOverlayLayer = null;
  const toolbar = document.getElementById('imagery-toolbar');
  if (toolbar) toolbar.style.display = 'none';
  const card = document.getElementById('imagery-card');
  if (card) card.style.display = 'none';
}

function setRasterDisplayMode(mode) {
  currentRasterMode = mode;
  document.querySelectorAll('.layer-toggle-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.btn-chip').forEach(btn => btn.classList.remove('active'));

  if (rgbOverlayLayer && map.hasLayer(rgbOverlayLayer)) map.removeLayer(rgbOverlayLayer);
  if (ndviOverlayLayer && map.hasLayer(ndviOverlayLayer)) map.removeLayer(ndviOverlayLayer);
  if (faiOverlayLayer && map.hasLayer(faiOverlayLayer)) map.removeLayer(faiOverlayLayer);

  const previewImg = document.getElementById('imagery-preview-img');
  const modeTag = document.getElementById('imagery-mode-tag');

  if (mode === 'rgb' && rgbOverlayLayer && latestAnalysisData?.rgb_image) {
    rgbOverlayLayer.addTo(map);
    rgbOverlayLayer.setOpacity(currentOpacity);
    document.getElementById('layer-rgb-btn')?.classList.add('active');
    document.getElementById('preview-rgb-btn')?.classList.add('active');
    if (previewImg) previewImg.src = latestAnalysisData.rgb_image;
    if (modeTag) modeTag.textContent = 'True Color (RGB)';
    if (activeLayer && activeLayer.setStyle) activeLayer.setStyle({ fillOpacity: 0.05, weight: 2 });
  } else if (mode === 'ndvi' && ndviOverlayLayer && latestAnalysisData?.ndvi_image) {
    ndviOverlayLayer.addTo(map);
    ndviOverlayLayer.setOpacity(currentOpacity);
    document.getElementById('layer-ndvi-btn')?.classList.add('active');
    document.getElementById('preview-ndvi-btn')?.classList.add('active');
    if (previewImg) previewImg.src = latestAnalysisData.ndvi_image;
    if (modeTag) modeTag.textContent = 'False Color NDVI Heatmap';
    if (activeLayer && activeLayer.setStyle) activeLayer.setStyle({ fillOpacity: 0.05, weight: 2 });
  } else if (mode === 'fai' && faiOverlayLayer && latestAnalysisData?.fai_image) {
    faiOverlayLayer.addTo(map);
    faiOverlayLayer.setOpacity(currentOpacity);
    document.getElementById('layer-fai-btn')?.classList.add('active');
    document.getElementById('preview-fai-btn')?.classList.add('active');
    if (previewImg) previewImg.src = latestAnalysisData.fai_image;
    if (modeTag) modeTag.textContent = 'Floating Algal Index (FAI / Macroalgae Heatmap)';
    if (activeLayer && activeLayer.setStyle) activeLayer.setStyle({ fillOpacity: 0.05, weight: 2 });
  } else {
    document.getElementById('layer-poly-btn')?.classList.add('active');
    if (activeLayer && activeLayer.setStyle) activeLayer.setStyle({ fillOpacity: 0.45, weight: 3 });
  }
}

function setupRasterOverlays(data) {
  clearRasterOverlays();
  if (!data.image_bounds) return;

  const bounds = L.latLngBounds(data.image_bounds);
  if (data.rgb_image) {
    rgbOverlayLayer = L.imageOverlay(data.rgb_image, bounds, { opacity: currentOpacity });
  }
  if (data.ndvi_image) {
    ndviOverlayLayer = L.imageOverlay(data.ndvi_image, bounds, { opacity: currentOpacity });
  }
  if (data.fai_image) {
    faiOverlayLayer = L.imageOverlay(data.fai_image, bounds, { opacity: currentOpacity });
  }

  const toolbar = document.getElementById('imagery-toolbar');
  if (toolbar) toolbar.style.display = 'flex';

  const card = document.getElementById('imagery-card');
  if (card && (data.rgb_image || data.ndvi_image || data.fai_image)) {
    card.style.display = 'block';
    const previewImg = document.getElementById('imagery-preview-img');
    if (previewImg) previewImg.src = data.rgb_image || data.ndvi_image || data.fai_image;
    const metaDate = document.getElementById('imagery-meta-date');
    if (metaDate) metaDate.textContent = `Date: ${data.satellite_info?.scene_date || '--'}`;
  }

  // Auto-switch to FAI if marine/coastal, otherwise default to RGB
  if (data.mariculture && data.mariculture.is_coastal && data.fai_image) {
    setRasterDisplayMode('fai');
  } else {
    setRasterDisplayMode('rgb');
  }
}

function runStepperAnimation() {
  const stepper = document.getElementById('pipeline-stepper');
  if (!stepper) return null;
  stepper.style.display = 'flex';
  const steps = [
    document.getElementById('step-1'),
    document.getElementById('step-2'),
    document.getElementById('step-3'),
    document.getElementById('step-4')
  ];
  steps.forEach(s => { if (s) s.className = 'step pending'; });
  if (steps[0]) steps[0].className = 'step active';

  let currentStep = 0;
  const interval = setInterval(() => {
    if (currentStep < steps.length) {
      if (steps[currentStep]) steps[currentStep].className = 'step completed';
      currentStep++;
      if (currentStep < steps.length && steps[currentStep]) {
        steps[currentStep].className = 'step active';
      }
    }
  }, 700);

  return {
    finish: () => {
      clearInterval(interval);
      steps.forEach(s => { if (s) s.className = 'step completed'; });
      setTimeout(() => {
        stepper.style.display = 'none';
      }, 400);
    },
    fail: () => {
      clearInterval(interval);
      stepper.style.display = 'none';
    }
  };
}

// Handle AOI Creation
map.on(L.Draw.Event.CREATED, function (e) {
  clearRasterOverlays();
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
  document.getElementById('aoi-status').textContent = 'AOI LOCKED // READY';
  document.getElementById('aoi-status').style.color = 'var(--accent)';

  document.getElementById('analyze-btn').disabled = false;
});

let latestAnalysisData = null;

map.on(L.Draw.Event.DELETED, function () {
  activeLayer = null;
  latestAnalysisData = null;
  clearRasterOverlays();
  document.getElementById('coord-display').textContent = '--';
  document.getElementById('bbox-display').textContent = '--';
  document.getElementById('area-display').textContent = '-- sq km';
  document.getElementById('aoi-status').textContent = 'NO AOI SELECTED';
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

// Wire raster toolbar and viewer controls
document.getElementById('layer-rgb-btn')?.addEventListener('click', () => setRasterDisplayMode('rgb'));
document.getElementById('layer-ndvi-btn')?.addEventListener('click', () => setRasterDisplayMode('ndvi'));
document.getElementById('layer-fai-btn')?.addEventListener('click', () => setRasterDisplayMode('fai'));
document.getElementById('layer-poly-btn')?.addEventListener('click', () => setRasterDisplayMode('thematic'));
document.getElementById('preview-rgb-btn')?.addEventListener('click', () => setRasterDisplayMode('rgb'));
document.getElementById('preview-ndvi-btn')?.addEventListener('click', () => setRasterDisplayMode('ndvi'));
document.getElementById('preview-fai-btn')?.addEventListener('click', () => setRasterDisplayMode('fai'));

const opacityInput = document.getElementById('layer-opacity');
if (opacityInput) {
  opacityInput.addEventListener('input', (e) => {
    currentOpacity = parseFloat(e.target.value) / 100.0;
    const opVal = document.getElementById('opacity-val');
    if (opVal) opVal.textContent = `${e.target.value}%`;
    if (rgbOverlayLayer) rgbOverlayLayer.setOpacity(currentOpacity);
    if (ndviOverlayLayer) ndviOverlayLayer.setOpacity(currentOpacity);
    if (faiOverlayLayer) faiOverlayLayer.setOpacity(currentOpacity);
  });
}

// ClimaCrew Indian Coastal Mariculture Hub Selectors
document.querySelectorAll('.target-hub-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const lat = parseFloat(btn.dataset.lat);
    const lon = parseFloat(btn.dataset.lon);
    const name = btn.dataset.name;
    map.setView([lat, lon], 12);
    
    clearRasterOverlays();
    drawnItems.clearLayers();
    const bounds = L.latLngBounds([[lat - 0.04, lon - 0.04], [lat + 0.04, lon + 0.04]]);
    activeLayer = L.rectangle(bounds, { color: '#00f0ff', weight: 2, fillOpacity: 0.2 });
    drawnItems.addLayer(activeLayer);
    
    const center = bounds.getCenter();
    const areaSqKm = (L.GeometryUtil.geodesicArea(activeLayer.getLatLngs()[0]) / 1000000).toFixed(2);
    document.getElementById('coord-display').textContent = `${center.lat.toFixed(4)}, ${center.lng.toFixed(4)}`;
    document.getElementById('bbox-display').textContent = `${bounds.getSouthWest().lat.toFixed(2)},${bounds.getSouthWest().lng.toFixed(2)} to ${bounds.getNorthEast().lat.toFixed(2)},${bounds.getNorthEast().lng.toFixed(2)}`;
    document.getElementById('area-display').textContent = `${areaSqKm} sq km`;
    document.getElementById('aoi-status').textContent = `LOCKED // ${name.toUpperCase()}`;
    document.getElementById('aoi-status').style.color = 'var(--accent)';
    document.getElementById('analyze-btn').disabled = false;
    
    document.getElementById('analyze-btn').click();
  });
});

// Analyze button handler - calls Python FastAPI endpoint
document.getElementById('analyze-btn').addEventListener('click', async () => {
  if (!activeLayer) return;

  const btn = document.getElementById('analyze-btn');
  btn.disabled = true;
  btn.innerHTML = '<span>⌖</span> INGESTING TELEMETRY...';

  const geojson = activeLayer.toGeoJSON();
  const date = document.getElementById('sat-date').value;

  const stepper = runStepperAnimation();

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
    stepper?.finish();
    renderResults(data);
    setupRasterOverlays(data);

    document.getElementById('report-btn').disabled = false;
    const headerBtn = document.getElementById('header-report-btn');
    if (headerBtn) headerBtn.style.display = 'inline-block';
  } catch (err) {
    stepper?.fail();
    console.error('Analysis failed:', err);
    alert(`Analysis failed: ${err.message || 'Make sure the Python server is running!'}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">⌖</span> ANALYZE AOI';
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

  // Render ClimaCrew Mariculture & Blue Carbon Intelligence
  renderMaricultureCard(data.mariculture);
}

function renderMaricultureCard(mariculture) {
  const container = document.getElementById('mariculture-container');
  const badge = document.getElementById('mariculture-badge');
  if (!container) return;

  if (!mariculture || !mariculture.is_coastal) {
    if (badge) {
      badge.textContent = 'INLAND AOI';
      badge.className = 'badge';
    }
    container.innerHTML = `
      <p class="placeholder-text">Selected AOI is predominantly inland terrestrial. Select a coastal hotspot (e.g. Palk Bay, Gulf of Kutch) or draw an AOI over marine waters to assess mariculture feasibility & Blue Carbon sequestration.</p>
    `;
    return;
  }

  if (badge) {
    badge.textContent = `MCDA: ${mariculture.suitability_score}%`;
    badge.className = mariculture.suitability_score >= 80 ? 'badge badge-success' : 'badge';
  }

  const speciesHtml = (mariculture.recommended_species || []).map(sp => `
    <div class="species-chip">🌿 ${sp}</div>
  `).join('');

  container.innerHTML = `
    <div class="mariculture-hud">
      <div class="hud-status-row">
        <span class="hud-tier-label">${mariculture.feasibility_tier}</span>
        <span class="hud-score-val mono">${mariculture.suitability_score}/100</span>
      </div>
      <div class="stat-bar" style="margin-bottom: 0.8rem;">
        <div class="stat-fill" style="width: ${mariculture.suitability_score}%; background: ${mariculture.suitability_score >= 80 ? '#00f0ff' : '#f59e0b'};"></div>
      </div>

      <div class="info-grid mono">
        <div><label>Marine Water Surface:</label> <span>${mariculture.water_area_ha?.toLocaleString()} ha</span></div>
        <div><label>Optical Water Clarity:</label> <span>${mariculture.water_clarity}</span></div>
        <div><label>Chlorophyll-a Proxy:</label> <span>${mariculture.estimated_chlorophyll_mg_m3} mg/m³</span></div>
        <div><label>Est. Wet Biomass Yield:</label> <span style="color:#00f0ff;">${mariculture.wet_biomass_annual_tonnes?.toLocaleString()} MT/yr</span></div>
        <div><label>Projected Blue Carbon (CO₂e):</label> <span style="color:#10b981;">${mariculture.co2_sequestered_t_annual?.toLocaleString()} tCO₂e/yr</span></div>
        <div><label>Coastal Livelihoods Supported:</label> <span>${mariculture.coastal_jobs_supported?.toLocaleString()} fisherfolk</span></div>
      </div>

      <div style="margin-top: 0.75rem;">
        <label class="chip-label" style="display:block; margin-bottom: 0.35rem; font-size: 0.7rem; color: var(--text-secondary);">RECOMMENDED MARICULTURE SPECIES:</label>
        <div style="display:flex; flex-direction:column; gap:0.3rem;">
          ${speciesHtml}
        </div>
      </div>

      <p class="mariculture-desc" style="margin-top: 0.75rem; font-size: 0.78rem; line-height: 1.45; color: var(--text-secondary);">
        ${mariculture.summary}
      </p>
    </div>
  `;
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
  const imageryHtml = data.rgb_image ? `
    <div class="report-section">
      <h3>2. Earth Observation Imagery (10m Resolution)</h3>
      <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 220px;">
          <div style="font-size: 0.78rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.4rem;">True Color Composite (RGB)</div>
          <img src="${data.rgb_image}" style="width: 100%; max-height: 190px; object-fit: cover; border-radius: 6px; border: 1px solid var(--glass-border);" alt="True Color Satellite Imagery" />
        </div>
        ${data.ndvi_image ? `
        <div style="flex: 1; min-width: 220px;">
          <div style="font-size: 0.78rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.4rem;">Multispectral NDVI False-Color Heatmap</div>
          <img src="${data.ndvi_image}" style="width: 100%; max-height: 190px; object-fit: cover; border-radius: 6px; border: 1px solid var(--glass-border);" alt="NDVI Heatmap" />
        </div>
        ` : ''}
        ${data.fai_image ? `
        <div style="flex: 1; min-width: 220px;">
          <div style="font-size: 0.78rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.4rem;">Floating Algal Index (FAI / Macroalgae Heatmap)</div>
          <img src="${data.fai_image}" style="width: 100%; max-height: 190px; object-fit: cover; border-radius: 6px; border: 1px solid var(--glass-border);" alt="FAI Algal Heatmap" />
        </div>
        ` : ''}
      </div>
    </div>
  ` : '';

  const maricultureHtml = data.mariculture && data.mariculture.is_coastal ? `
    <div class="report-section">
      <h3>3. Blue Carbon MRV &amp; Coastal Mariculture Feasibility (ClimaCrew Model)</h3>
      <div class="report-grid-2">
        <div><label>Site Suitability Index (MCDA):</label> <span style="font-weight:700; color:#00f0ff;">${data.mariculture.suitability_score}% (${data.mariculture.feasibility_tier})</span></div>
        <div><label>Marine Farming Water Area:</label> <span>${data.mariculture.water_area_ha?.toLocaleString()} ha</span></div>
        <div><label>Optical Water Clarity:</label> <span>${data.mariculture.water_clarity}</span></div>
        <div><label>Chlorophyll-a Proxy:</label> <span>${data.mariculture.estimated_chlorophyll_mg_m3} mg/m³</span></div>
        <div><label>Est. Annual Wet Biomass:</label> <span style="font-weight:700; color:#00f0ff;">${data.mariculture.wet_biomass_annual_tonnes?.toLocaleString()} MT / year</span></div>
        <div><label>Projected Blue Carbon (CO₂e):</label> <span style="font-weight:700; color:#10b981;">${data.mariculture.co2_sequestered_t_annual?.toLocaleString()} tCO₂e / year</span></div>
        <div><label>Coastal Livelihoods Supported:</label> <span>${data.mariculture.coastal_jobs_supported?.toLocaleString()} fisherfolk</span></div>
      </div>
      <div style="margin-top: 0.6rem; font-size: 0.8rem; line-height: 1.4;">
        <strong>Recommended Cultivars:</strong> ${data.mariculture.recommended_species?.join(' • ')}
      </div>
      <div class="report-callout" style="margin-top: 0.6rem;">
        ${data.mariculture.summary}
      </div>
    </div>
  ` : '';

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

      ${imageryHtml}

      ${maricultureHtml}

      <div class="report-section">
        <h3>${maricultureHtml ? '4' : '3'}. Biophysical Land Cover Distribution</h3>
        <div class="report-distribution-bar">
          ${distBars}
        </div>
        <div class="report-legend">
          ${distLegend}
        </div>
      </div>

      <div class="report-section">
        <h3>${maricultureHtml ? '5' : '4'}. Geomorphological & Structural Landscape Assessment</h3>
        ${interpHtml}
      </div>

      <div class="report-section">
        <h3>${maricultureHtml ? '6' : '5'}. Ground-Truth Academic Research & Field Surveys (OpenAlex)</h3>
        ${litHtml}
      </div>

      <div class="report-footer-notice">
        GeoSentinel AI Tactical Platform • Sentinel-2 L2A BOA Multispectral Analytics • ClimaCrew Blue Economy Extension
      </div>
    `;
  }
}
