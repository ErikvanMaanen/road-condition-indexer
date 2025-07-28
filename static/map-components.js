/**
 * Centralized Map Configuration and Utilities
 * 
 * This module provides standardized map configuration, styling, and utility functions
 * to eliminate code duplication across different HTML files.
 */

// Map Component Configuration
const MAP_CONFIG = {
    // Default map settings
    defaults: {
        center: [52.028, 5.168], // Houten, NL
        zoom: 15,
        enableGeolocation: true,
        enableBicycleMarker: false,
        enableFullscreen: true,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    },
    
    // Tile layer configuration
    tileLayer: {
        url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        options: {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }
    },
    
    // Geolocation options
    geoOptions: {
        enableHighAccuracy: true,
        maximumAge: 0,
        timeout: 10000
    }
};

// Map Component HTML Templates
const MAP_TEMPLATES = {
    // Basic map container with scale and filter
    basic: `
        <div id="map"></div>
        <div id="scale-container">
            <span>Smooth</span>
            <div id="scale-bar"></div>
            <span>Rough</span>
        </div>
        <div id="roughness-filter-container" style="margin-bottom: 0.5rem;">
            <select id="roughness-filter" multiple style="min-width: 120px;">
                <option value="">[All Roughness]</option>
                <option value="1">1 - Smooth road</option>
                <option value="2">2 - Even surface</option>
                <option value="3">3 - Light texture</option>
                <option value="4">4 - Coarse texture</option>
                <option value="5">5 - Moderate roughness</option>
                <option value="6">6 - Bumpy cobbles</option>
                <option value="7">7 - Fine gravel</option>
                <option value="8">8 - Coarse gravel</option>
                <option value="9">9 - Severely uneven</option>
                <option value="10">10 - Extremely rough</option>
            </select>
        </div>`,
    
    // Simple map container without filters (for testing)
    simple: `
        <div id="map"></div>
        <div id="scale-container">
            <span>Smooth</span>
            <div id="scale-bar"></div>
            <span>Rough</span>
        </div>`
};

// Map Component CSS Styles
const MAP_STYLES = `
/* Map Component Styles */
#map {
    width: 100%;
    height: 40vh;
    margin-bottom: 1rem;
    border: 1px solid #ccc;
}

#map:fullscreen {
    width: 100% !important;
    height: 100% !important;
    z-index: 9999;
}

/* Fullscreen button styling */
.fullscreen-btn {
    background: white;
    border: 2px solid rgba(0,0,0,0.2);
    border-radius: 4px;
    color: #333;
    font-size: 18px;
    width: 34px;
    height: 34px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 1px 5px rgba(0,0,0,0.15);
    transition: all 0.2s ease;
}

.fullscreen-btn:hover {
    background: #f4f4f4;
    border-color: rgba(0,0,0,0.4);
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
}

.fullscreen-btn:active {
    transform: translateY(1px);
}

#scale-container {
    display: flex;
    align-items: center;
    margin-bottom: 1rem;
    gap: 0.5rem;
}

#scale-bar {
    flex: 1;
    height: 12px;
    background: linear-gradient(to right, green, yellow, red);
    border: 1px solid #ccc;
}

#roughness-filter-container {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
}

#roughness-filter {
    padding: 0.25rem;
    border: 1px solid #ccc;
    border-radius: 3px;
    background: white;
    min-width: 120px;
}

/* Bicycle marker animation */
.bicycle-pulse {
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% {
        transform: scale(1);
        opacity: 1;
    }
    50% {
        transform: scale(1.1);
        opacity: 0.7;
    }
    100% {
        transform: scale(1);
        opacity: 1;
    }
}

/* Responsive design */
@media (max-width: 768px) {
    #map {
        height: 50vh;
    }
    
    #roughness-filter-container {
        flex-direction: column;
        align-items: flex-start;
    }
    
    #roughness-filter {
        min-width: 100%;
    }
}`;

/**
 * Inject map component styles into the document head
 */
function injectMapStyles() {
    // Check if styles are already injected
    if (document.getElementById('map-component-styles')) {
        return;
    }
    
    const styleElement = document.createElement('style');
    styleElement.id = 'map-component-styles';
    styleElement.textContent = MAP_STYLES;
    document.head.appendChild(styleElement);
}

/**
 * Create a map container with the specified template
 * @param {string} containerId - ID of the container element
 * @param {string} template - Template name ('basic' or 'simple')
 */
function createMapContainer(containerId, template = 'basic') {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Map container '${containerId}' not found`);
        return false;
    }
    
    // Inject styles
    injectMapStyles();
    
    // Insert template HTML
    container.innerHTML = MAP_TEMPLATES[template] || MAP_TEMPLATES.basic;
    
    return true;
}

/**
 * Create fallback map when partial loading fails
 * @param {string} containerId - ID of the map container
 */
function createFallbackMap(containerId = 'map-container') {
    console.warn('Creating fallback map');
    
    // Create basic map container
    if (!createMapContainer(containerId, 'simple')) {
        return null;
    }
    
    // Ensure Leaflet is available
    if (typeof L === 'undefined') {
        console.error('Leaflet library not loaded');
        return null;
    }
    
    // Create basic map
    const map = L.map('map');
    L.tileLayer(MAP_CONFIG.tileLayer.url, {
        attribution: MAP_CONFIG.tileLayer.options.attribution
    }).addTo(map);
    
    map.setView(MAP_CONFIG.defaults.center, MAP_CONFIG.defaults.zoom);
    
    // Store map globally
    window.map = map;
    
    // Add basic fullscreen control if available
    if (typeof addFullscreenControl === 'function') {
        addFullscreenControl(map);
    }
    
    // Add basic functions for compatibility
    window.clearMapData = function() {
        if (window.map) {
            window.map.eachLayer(layer => {
                if (layer instanceof L.CircleMarker || layer instanceof L.Polyline) {
                    window.map.removeLayer(layer);
                }
            });
        }
    };
    
    window.updateBicycleMarker = function(coords, info = {}) {
        // Basic implementation - can be enhanced as needed
        console.log('updateBicycleMarker called with:', coords, info);
    };
    
    return map;
}

/**
 * Load map partial with fallback
 * @param {string} containerId - ID of the container element
 * @param {string} partialUrl - URL of the map partial
 * @returns {Promise<boolean>} Success status
 */
async function loadMapPartial(containerId = 'map-container', partialUrl = 'map-partial.html') {
    try {
        const mapContainer = document.getElementById(containerId);
        if (!mapContainer) {
            console.error(`Map container '${containerId}' not found`);
            return false;
        }

        const response = await fetch(partialUrl);
        if (!response.ok) {
            throw new Error(`Failed to load ${partialUrl}: ${response.status} ${response.statusText}`);
        }

        const mapHtml = await response.text();
        
        // Parse the HTML to extract script content
        const parser = new DOMParser();
        const doc = parser.parseFromString(mapHtml, 'text/html');
        
        // Insert the HTML content (excluding scripts)
        const scripts = doc.querySelectorAll('script');
        const styles = doc.querySelectorAll('style');
        
        // Remove scripts and styles from the content to insert them separately
        scripts.forEach(script => script.remove());
        styles.forEach(style => style.remove());
        
        // Insert the HTML content
        mapContainer.innerHTML = doc.body.innerHTML;
        
        // Insert and execute styles
        styles.forEach(style => {
            const newStyle = document.createElement('style');
            newStyle.textContent = style.textContent;
            document.head.appendChild(newStyle);
        });
        
        // Insert and execute scripts
        for (const script of scripts) {
            const newScript = document.createElement('script');
            newScript.textContent = script.textContent;
            document.head.appendChild(newScript);
            
            // Wait a moment for script to execute
            await new Promise(resolve => setTimeout(resolve, 10));
        }
        
        return true;
    } catch (error) {
        console.error('Failed to load map partial:', error);
        if (typeof addDebug === 'function') {
            addDebug('Map partial loading error: ' + error.message, 'System', 'ERROR');
        }
        return false;
    }
}

/**
 * Initialize map with automatic fallback
 * @param {Object} options - Map initialization options
 * @param {string} containerId - ID of the container element
 * @returns {Promise<Object>} Map instance or null
 */
async function initializeMapWithFallback(options = {}, containerId = 'map-container') {
    // Inject styles first
    injectMapStyles();
    
    // Try to load map partial first
    const partialLoaded = await loadMapPartial(containerId);
    
    if (partialLoaded) {
        // Wait for map functions to be available
        let attempts = 0;
        const maxAttempts = 50; // 5 seconds max
        
        while (typeof initializeStandardMap !== 'function' && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }
        
        if (typeof initializeStandardMap === 'function') {
            return initializeStandardMap(options);
        }
    }
    
    // Fallback to basic map
    console.warn('Map partial failed to load, using fallback');
    return createFallbackMap(containerId);
}

// Export functions to global scope
window.MAP_CONFIG = MAP_CONFIG;
window.MAP_TEMPLATES = MAP_TEMPLATES;
window.injectMapStyles = injectMapStyles;
window.createMapContainer = createMapContainer;
window.createFallbackMap = createFallbackMap;
window.loadMapPartial = loadMapPartial;
window.initializeMapWithFallback = initializeMapWithFallback;

// Export clearMapData function globally for compatibility
window.clearMapData = function() {
    if (window.map) {
        window.map.eachLayer(layer => {
            if (layer instanceof L.CircleMarker || layer instanceof L.Polyline) {
                window.map.removeLayer(layer);
            }
        });
    }
};
