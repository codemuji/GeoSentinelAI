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

// Live Mouse Coordinate Readout (Unprojecting screen pixels to WGS84 EPSG:4326 Lat/Lng)
map.on('mousemove', (e) => {
  const lat = e.latlng.lat.toFixed(4);
  const lng = e.latlng.lng.toFixed(4);
  const latDir = lat >= 0 ? 'N' : 'S';
  const lngDir = lng >= 0 ? 'E' : 'W';
  document.getElementById('mouse-coords').textContent = `Cursor Coordinates: ${Math.abs(lat)}° ${latDir}, ${Math.abs(lng)}° ${lngDir}`;
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

map.on(L.Draw.Event.DELETED, function () {
  activeLayer = null;
  document.getElementById('coord-display').textContent = '--';
  document.getElementById('bbox-display').textContent = '--';
  document.getElementById('area-display').textContent = '-- sq km';
  document.getElementById('aoi-status').textContent = 'No AOI Selected';
  document.getElementById('aoi-status').style.color = 'var(--text-secondary)';
  document.getElementById('analyze-btn').disabled = true;
  document.getElementById('report-btn').disabled = true;
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
    
    const data = await res.json();
    renderResults(data);
    document.getElementById('report-btn').disabled = false;
  } catch (err) {
    console.error('Analysis failed:', err);
    alert('Analysis failed or backend is offline. Make sure the Python server is running!');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>⚡</span> Analyze AOI';
  }
});

function renderResults(data) {
  // Populate Real Satellite Metadata if available
  if (data.satellite_info) {
    document.getElementById('scene-display').textContent = data.satellite_info.scene_id || '--';
    document.getElementById('capture-display').textContent = data.satellite_info.scene_date || '--';
    document.getElementById('cloud-display').textContent = `${data.satellite_info.cloud_cover || 0}%`;
    document.getElementById('ndvi-display').textContent = `${data.satellite_info.ndvi_mean || 0}`;
    document.getElementById('source-display').textContent = data.satellite_info.source || 'Sentinel-2 L2A';
  }

  // Render Land Cover Stats
  const statsContainer = document.getElementById('stats-container');
  statsContainer.innerHTML = '';

  const colors = {
    'Forest': '#10b981',
    'Agriculture': '#eab308',
    'Water': '#3b82f6',
    'Bare Soil': '#a855f7',
    'Urban': '#ef4444'
  };

  for (const [class_name, percent] of Object.entries(data.land_cover)) {
    const div = document.createElement('div');
    div.className = 'stat-item';
    div.innerHTML = `
      <div class="stat-label">
        <span>${class_name}</span>
        <span>${percent}%</span>
      </div>
      <div class="stat-bar">
        <div class="stat-fill" style="width: ${percent}%; background: ${colors[class_name] || '#00f0ff'};"></div>
      </div>
    `;
    statsContainer.appendChild(div);
  }

  // Render Geological Interpretations
  const geologyContainer = document.getElementById('geology-container');
  geologyContainer.innerHTML = '';

  data.interpretations.forEach(item => {
    const div = document.createElement('div');
    div.className = 'interpretation-item';
    div.innerHTML = `
      <div>${item.text}</div>
      <div class="confidence">Confidence: ${(item.confidence * 100).toFixed(0)}% • AI-assisted interpretation</div>
    `;
    geologyContainer.appendChild(div);
  });
}
