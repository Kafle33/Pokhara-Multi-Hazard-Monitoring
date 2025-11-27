/**
 * Pokhara Multi-Hazard Monitoring System - Frontend Application
 * Leaflet map with dynamic layer loading and interaction
 */

// Configuration
const CONFIG = {
    API_BASE_URL: window.location.origin,
    DEFAULT_CENTER: [28.2096, 83.9856], // Pokhara, Nepal
    DEFAULT_ZOOM: 12,
    MAX_ZOOM: 18,
};

// Color mapping for hazard classes
const COLORS = {
    very_low: '#2ECC71',
    low: '#F1C40F',
    moderate: '#E67E22',
    high: '#E74C3C',
    very_high: '#8E44AD',
    flood: '#3498DB',
    no_flood: 'transparent'
};

// Global variables
let map;
let baseLayers = {};
let overlayLayers = {};
let currentBasemap = 'openstreetmap';

/**
 * Initialize the Leaflet map
 */
function initMap() {
    // Create map
    map = L.map('map', {
        center: CONFIG.DEFAULT_CENTER,
        zoom: CONFIG.DEFAULT_ZOOM,
        maxZoom: CONFIG.MAX_ZOOM,
        zoomControl: true
    });

    // Define basemaps
    baseLayers = {
        openstreetmap: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }),
        satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Esri, DigitalGlobe, GeoEye, Earthstar Geographics',
            maxZoom: 19
        }),
        terrain: L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenTopoMap contributors',
            maxZoom: 17
        }),
        dark: L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '© CARTO',
            maxZoom: 19
        })
    };

    // Add default basemap
    baseLayers[currentBasemap].addTo(map);

    // Setup event listeners
    setupEventListeners();

    console.log('Map initialized');
}

/**
 * Setup event listeners for layer controls and basemap selector
 */
function setupEventListeners() {
    // Layer checkboxes
    document.querySelectorAll('.layer-checkbox input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', handleLayerToggle);
    });

    // Basemap selector
    document.getElementById('basemap-select').addEventListener('change', handleBasemapChange);
}

/**
 * Handle layer toggle (checkbox change)
 */
async function handleLayerToggle(event) {
    const checkbox = event.target;
    const layerName = checkbox.dataset.layer;

    if (checkbox.checked) {
        await loadLayer(layerName);
    } else {
        removeLayer(layerName);
    }
}

/**
 * Load GeoJSON layer from API
 */
async function loadLayer(layerName) {
    showLoading();

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/api/layers/${layerName}`);

        if (!response.ok) {
            throw new Error(`Failed to load layer: ${response.statusText}`);
        }

        const geojson = await response.json();

        // Create GeoJSON layer with styling
        const layer = L.geoJSON(geojson, {
            style: (feature) => getFeatureStyle(feature, layerName),
            onEachFeature: (feature, layer) => bindPopup(feature, layer, layerName)
        });

        // Add to map
        layer.addTo(map);

        // Store reference
        overlayLayers[layerName] = layer;

        // Zoom to layer bounds
        if (layer.getBounds().isValid()) {
            map.fitBounds(layer.getBounds(), { padding: [50, 50] });
        }

        updateInfoPanel(`Loaded layer: ${formatLayerName(layerName)}`);
        console.log(`Layer loaded: ${layerName}`);

    } catch (error) {
        console.error(`Error loading layer ${layerName}:`, error);
        alert(`Failed to load layer: ${layerName}\n${error.message}`);

        // Uncheck the checkbox
        const checkbox = document.querySelector(`input[data-layer="${layerName}"]`);
        if (checkbox) checkbox.checked = false;

    } finally {
        hideLoading();
    }
}

/**
 * Remove layer from map
 */
function removeLayer(layerName) {
    if (overlayLayers[layerName]) {
        map.removeLayer(overlayLayers[layerName]);
        delete overlayLayers[layerName];
        updateInfoPanel(`Removed layer: ${formatLayerName(layerName)}`);
        console.log(`Layer removed: ${layerName}`);
    }
}

/**
 * Get style for GeoJSON feature
 */
function getFeatureStyle(feature, layerName) {
    const className = feature.properties.class || 'unknown';
    const color = COLORS[className] || '#888888';

    // Determine opacity based on layer type
    let fillOpacity = 0.6;
    let opacity = 0.8;

    if (layerName.includes('flood')) {
        fillOpacity = className === 'flood' ? 0.7 : 0;
        opacity = className === 'flood' ? 0.9 : 0;
    }

    return {
        fillColor: color,
        fillOpacity: fillOpacity,
        color: color,
        weight: 2,
        opacity: opacity
    };
}

/**
 * Bind popup to feature
 */
function bindPopup(feature, layer, layerName) {
    const props = feature.properties;

    // Build popup content
    let content = `<h3>${formatLayerName(layerName)}</h3>`;
    content += `<strong>Class:</strong> ${formatClassName(props.class || 'Unknown')}<br>`;

    // Add value if available
    if (props.value !== undefined) {
        content += `<strong>Value:</strong> ${props.value}<br>`;
    }

    // Add area if available
    if (props.area !== undefined) {
        content += `<strong>Area:</strong> ${props.area.toFixed(2)} ${props.area_unit || 'm²'}<br>`;
    }

    layer.bindPopup(content);

    // Hover effect
    layer.on('mouseover', function () {
        this.setStyle({ weight: 3, fillOpacity: 0.8 });
    });

    layer.on('mouseout', function () {
        this.setStyle(getFeatureStyle(feature, layerName));
    });
}

/**
 * Handle basemap change
 */
function handleBasemapChange(event) {
    const newBasemap = event.target.value;

    // Remove current basemap
    map.removeLayer(baseLayers[currentBasemap]);

    // Add new basemap
    baseLayers[newBasemap].addTo(map);

    // Update current
    currentBasemap = newBasemap;

    console.log(`Basemap changed to: ${newBasemap}`);
}

/**
 * Update info panel content
 */
function updateInfoPanel(message) {
    const infoContent = document.getElementById('info-content');
    infoContent.innerHTML = `<p>${message}</p>`;
}

/**
 * Format layer name for display
 */
function formatLayerName(layerName) {
    return layerName
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Format class name for display
 */
function formatClassName(className) {
    return className
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Show loading overlay
 */
function showLoading() {
    document.getElementById('loading').style.display = 'flex';
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

/**
 * Fetch available layers from API
 */
async function fetchAvailableLayers() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/api/layers/list`);
        const data = await response.json();

        console.log(`Available layers: ${data.count}`);
        console.log(data.layers);

        return data.layers;
    } catch (error) {
        console.error('Error fetching layers:', error);
        return [];
    }
}

/**
 * Initialize application
 */
async function init() {
    console.log('Initializing Pokhara Multi-Hazard Monitoring System...');

    // Initialize map
    initMap();

    // Fetch available layers
    const layers = await fetchAvailableLayers();

    if (layers.length > 0) {
        updateInfoPanel(`${layers.length} layers available. Select layers from the panel to view.`);
    } else {
        updateInfoPanel('No processed layers available yet. Use the API to process hazard data.');
    }

    console.log('Initialization complete');
}

// Start application when DOM is ready
document.addEventListener('DOMContentLoaded', init);
