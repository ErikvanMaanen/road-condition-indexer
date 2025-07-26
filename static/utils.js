/**
 * Road Condition Indexer - Common Utilities
 * 
 * This file contains all common functions used across multiple HTML files
 * to eliminate code duplication and improve maintainability.
 */

// ============================================================================
// TIME AND DATE UTILITIES
// ============================================================================

// Common constants
const LABEL_COUNT = 10;
const ROUGHNESS_NAMES = [
    'Very Smooth', 'Smooth', 'Fairly Smooth', 'Moderate',
    'Slightly Rough', 'Rough', 'Very Rough', 'Extremely Rough',
    'Severely Rough', 'Impassable'
];

/**
 * Format time in Dutch timezone
 * @param {string} isoString - ISO date string
 * @returns {string} Formatted date string
 */
function formatDutchTime(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleString('nl-NL', {
            timeZone: 'Europe/Amsterdam',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (error) {
        return isoString; // Fallback to original string
    }
}

/**
 * Convert timestamp to CEST datetime-local format
 * @param {string|number} timestamp - Timestamp to convert
 * @returns {string} CEST datetime-local format
 */
function toCESTDateTimeLocal(timestamp) {
    try {
        const date = new Date(timestamp);
        const cesTime = new Date(date.toLocaleString("en-US", {timeZone: "Europe/Amsterdam"}));
        return cesTime.toISOString().slice(0, 16);
    } catch (error) {
        return '';
    }
}

/**
 * Convert CEST datetime-local input value back to UTC ISO
 * @param {string} datetimeLocalValue - datetime-local input value
 * @returns {string} UTC ISO string
 */
function fromCESTDateTimeLocal(datetimeLocalValue) {
    try {
        if (!datetimeLocalValue) return '';
        const localDate = new Date(datetimeLocalValue);
        const utcTime = localDate.getTime() + (localDate.getTimezoneOffset() * 60000);
        const cestOffset = 2 * 60 * 60 * 1000; // CEST is UTC+2
        const utcDate = new Date(utcTime + cestOffset);
        return utcDate.toISOString();
    } catch (error) {
        return '';
    }
}

/**
 * Format short date/time for logs
 * @returns {string} Short formatted date/time
 */
function formatShortDateTime() {
    const now = new Date();
    const cesTime = new Date(now.toLocaleString("en-US", {timeZone: "Europe/Amsterdam"}));
    const month = String(cesTime.getMonth() + 1).padStart(2, '0');
    const day = String(cesTime.getDate()).padStart(2, '0');
    const hours = String(cesTime.getHours()).padStart(2, '0');
    const minutes = String(cesTime.getMinutes()).padStart(2, '0');
    const seconds = String(cesTime.getSeconds()).padStart(2, '0');
    return `${month}/${day} ${hours}:${minutes}:${seconds}`;
}

// ============================================================================
// LOGGING UTILITIES
// ============================================================================

// Global logging variables (will be initialized by logs-partial.html)
window.allLogMessages = window.allLogMessages || [];
window.deviceId = window.deviceId || '';

/**
 * Add a simple log message (also appears in All Messages as INFO/General)
 * @param {string} msg - Message to log
 * @param {string} category - Message category (default: 'General')
 * @param {string} level - Log level (default: 'INFO')
 */
function addLog(msg, category = 'General', level = 'INFO') {
    addMessage(msg, level, category);
}

/**
 * Add debug message (legacy function for compatibility)
 * @param {string} msg - Message to log
 * @param {string} category - Message category (default: 'Debug')
 * @param {string} level - Log level (default: 'DEBUG')
 * @param {Error} error - Optional error object
 */
function addDebug(msg, category = 'Debug', level = 'DEBUG', error = null) {
    addMessage(msg, level, category, error);
}

/**
 * Add message to all messages with full details
 * @param {string} msg - Message to log
 * @param {string} level - Log level (default: 'INFO')
 * @param {string} category - Message category (default: 'General')
 * @param {Error} error - Optional error object
 */
function addMessage(msg, level = 'INFO', category = 'General', error = null) {
    const timestamp = formatShortDateTime();
    let messageText = msg;
    
    if (level === 'ERROR' && error && error.stack) {
        messageText += `\nStack: ${error.stack}`;
    }
    
    const logEntry = {
        timestamp,
        level,
        category,
        deviceId: window.deviceId.slice(-8) || 'unknown',
        message: messageText
    };
    
    window.allLogMessages = window.allLogMessages || [];
    window.allLogMessages.push(logEntry);
    
    // Limit to last 1000 messages to prevent memory issues
    if (window.allLogMessages.length > 1000) {
        window.allLogMessages = window.allLogMessages.slice(-1000);
    }
    
    // Update display if functions are available
    if (typeof updateDebugDisplay === 'function') {
        updateDebugDisplay();
    }
    if (typeof updateLogStats === 'function') {
        updateLogStats();
    }
}

// ============================================================================
// MAP AND VISUALIZATION UTILITIES
// ============================================================================

/**
 * Get color for roughness value
 * @param {number} r - Roughness value
 * @param {number} min - Minimum roughness value
 * @param {number} max - Maximum roughness value
 * @returns {string} RGB color string
 */
function colorForRoughness(r, min, max) {
    let ratio = 0;
    if (typeof min === 'number' && typeof max === 'number' && max !== min) {
        ratio = (r - min) / (max - min);
    } else if (window.roughAvg && window.roughAvg > 0) {
        ratio = r / (window.roughAvg * 2);
    } else if (window.roughMax !== window.roughMin) {
        ratio = r / window.roughMax;
    }
    ratio = Math.min(Math.max(ratio, 0), 1);
    const red = Math.floor(255 * ratio);
    const green = Math.floor(255 * (1 - ratio));
    return `rgb(${red},${green},0)`;
}

/**
 * Convert direction degrees to compass direction
 * @param {number} deg - Direction in degrees
 * @returns {string} Compass direction
 */
function directionToCompass(deg) {
    if (deg === null || isNaN(deg)) return 'N/A';
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const idx = Math.round((deg % 360) / 45) % 8;
    return directions[idx];
}

/**
 * Get roughness label for a value
 * @param {number} r - Roughness value
 * @returns {string} Roughness label
 */
function roughnessLabel(r) {
    let min = window.roughMin || 0;
    let max = window.roughMax || LABEL_COUNT;
    if (max === min) {
        max = min + 1;
    }
    const offset = 1;
    let logMin = Math.log(min + offset);
    let logMax = Math.log(max + offset);
    if (logMax === logMin) logMax = logMin + 1;
    const ratio = (Math.log(r + offset) - logMin) / (logMax - logMin);
    const idx = Math.max(0, Math.min(LABEL_COUNT - 1, Math.floor(ratio * LABEL_COUNT)));
    return String(idx + 1);
}

/**
 * Get roughness range for an index
 * @param {number} idx - Index (0-based)
 * @returns {Array} [low, high] roughness range
 */
function roughnessRange(idx) {
    let min = window.roughMin || 0;
    let max = window.roughMax || LABEL_COUNT;
    if (max === min) {
        max = min + 1;
    }
    const offset = 1;
    let logMin = Math.log(min + offset);
    let logMax = Math.log(max + offset);
    if (logMax === logMin) logMax = logMin + 1;
    const low = Math.exp((logMax - logMin) * idx / LABEL_COUNT + logMin) - offset;
    const high = Math.exp((logMax - logMin) * (idx + 1) / LABEL_COUNT + logMin) - offset;
    return [low, high];
}

/**
 * Update roughness labels in UI
 */
function updateRoughnessLabels() {
    const select = document.getElementById('roughness-filter');
    if (select) {
        for (let i = 0; i < LABEL_COUNT; i++) {
            const [low, high] = roughnessRange(i);
            const option = select.options[i + 1]; // +1 to skip "All" option
            if (option) {
                option.textContent = `${ROUGHNESS_NAMES[i]} (${low.toFixed(2)}-${high.toFixed(2)})`;
            }
        }
    }
    
    const items = document.querySelectorAll('#roughness-scale ol li');
    items.forEach((li, idx) => {
        const [low, high] = roughnessRange(idx);
        li.textContent = `${ROUGHNESS_NAMES[idx]} (${low.toFixed(2)}-${high.toFixed(2)})`;
    });
}

/**
 * Filter roughness value based on UI selection
 * @param {number} r - Roughness value
 * @returns {boolean} Whether the value passes the filter
 */
function filterRoughness(r) {
    const sel = document.getElementById('roughness-filter');
    if (!sel) return true;
    const values = Array.from(sel.selectedOptions).map(o => o.value).filter(v => v);
    if (values.length === 0) return true;
    return values.includes(roughnessLabel(r));
}

// ============================================================================
// LEAFLET MAP UTILITIES
// ============================================================================

/**
 * Add fullscreen control to map
 * @param {L.Map} m - Leaflet map instance
 */
function addFullscreenControl(m) {
    const Full = L.Control.extend({
        onAdd: function() {
            const button = L.DomUtil.create('button', 'fullscreen-btn');
            button.innerHTML = '⛶';
            button.title = 'Fullscreen';
            button.onclick = function() {
                if (document.fullscreenElement) {
                    document.exitFullscreen();
                    addLog('Exited fullscreen');
                } else {
                    document.documentElement.requestFullscreen();
                    addLog('Fullscreen button pressed');
                }
            };
            return button;
        }
    });
    m.addControl(new Full({ position: 'topleft' }));
}

/**
 * Add a point to the map
 * @param {number} lat - Latitude
 * @param {number} lon - Longitude
 * @param {number} roughness - Roughness value
 * @param {Object} info - Additional info object
 * @param {string} nickname - Device nickname
 * @param {number} min - Minimum roughness for color scaling
 * @param {number} max - Maximum roughness for color scaling
 */
function addPoint(lat, lon, roughness, info = null, nickname = '', min = null, max = null) {
    if (!window.map) return;
    
    const marker = L.circleMarker([lat, lon], {
        radius: 4,
        fillColor: colorForRoughness(roughness, min, max),
        color: colorForRoughness(roughness, min, max),
        weight: 1,
        opacity: 1,
        fillOpacity: 0.8
    });

    let popup = `Roughness: ${roughnessLabel(roughness)} (${roughness.toFixed(2)})`;
    if (info) {
        const timeStr = formatDutchTime(info.timestamp);
        popup = `Device: ${nickname || info.device_id}<br>` +
                `Time: ${timeStr}<br>` +
                `Speed: ${info.speed_kmh.toFixed(1)} km/h<br>` +
                `Dir: ${directionToCompass(info.direction)}<br>` +
                `Roughness: ${roughnessLabel(info.roughness)} (${info.roughness.toFixed(2)})`;
    }

    marker.bindPopup(popup);
    marker.addTo(window.map);
    
    if (window.markers) {
        window.markers.push(marker);
    }
}

// ============================================================================
// API AND DATA UTILITIES
// ============================================================================

/**
 * Authenticated fetch wrapper
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} Fetch response
 */
async function authFetch(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        credentials: 'include'
    });
    
    if (response.status === 401) {
        const currentUrl = encodeURIComponent(window.location.href);
        window.location.href = `/login.html?next=${currentUrl}`;
        return;
    }
    
    return response;
}

/**
 * Populate device IDs dropdown
 */
async function populateDeviceIds() {
    try {
        const response = await fetch('/device_ids');
        const deviceIds = await response.json();
        const select = document.getElementById('deviceId');
        if (!select) return;

        // Clear existing options except "All devices"
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }

        // Fetch nicknames
        const nicknameResponse = await fetch('/nickname');
        window.deviceNicknames = await nicknameResponse.json();

        deviceIds.forEach(id => {
            const option = document.createElement('option');
            option.value = id;
            const nickname = window.deviceNicknames[id];
            option.textContent = nickname ? `${nickname} (${id.slice(-8)})` : id.slice(-8);
            select.appendChild(option);
        });

        // Set current device if available
        const currentDeviceId = localStorage.getItem('deviceId');
        if (currentDeviceId && deviceIds.includes(currentDeviceId)) {
            select.value = currentDeviceId;
        }
    } catch (error) {
        addDebug('Error loading device IDs: ' + error.message, 'Network', 'ERROR');
    }
}

/**
 * Set date range based on selected device
 */
async function setDateRange() {
    const deviceId = document.getElementById('deviceId')?.value;
    if (!deviceId || deviceId === 'all') return;

    try {
        const response = await fetch(`/date_range?device_id=${encodeURIComponent(deviceId)}`);
        const data = await response.json();
        
        if (data.start) document.getElementById('startDate').value = toCESTDateTimeLocal(data.start);
        if (data.end) document.getElementById('endDate').value = toCESTDateTimeLocal(data.end);
        
        syncRanges();
    } catch (error) {
        addDebug('Error setting date range: ' + error.message, 'Network', 'ERROR');
    }
}

/**
 * Sync range sliders with date inputs
 */
function syncRanges() {
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    const startRange = document.getElementById('startRange');
    const endRange = document.getElementById('endRange');
    
    if (!startDate || !endDate || !startRange || !endRange) return;

    const startMs = new Date(startDate.value).getTime();
    const endMs = new Date(endDate.value).getTime();
    
    if (startMs && endMs && endMs > startMs) {
        window.sliderMin = startMs;
        window.sliderMax = endMs;
        
        startRange.min = startMs;
        startRange.max = endMs;
        startRange.value = startMs;
        
        endRange.min = startMs;
        endRange.max = endMs;
        endRange.value = endMs;
    }
}

/**
 * Load logs partial component
 */
async function loadLogsPartial() {
    try {
        const response = await fetch('/static/logs-partial.html');
        if (!response.ok) {
            addDebug('Failed to load logs partial: ' + response.statusText, 'System', 'WARNING');
            return;
        }
        
        const html = await response.text();
        const container = document.getElementById('logs-container');
        if (container) {
            container.innerHTML = html;
            
            // Initialize logs after loading
            if (typeof initializeLogs === 'function') {
                initializeLogs();
            }
        }
    } catch (error) {
        addDebug('Error loading logs partial: ' + error.message, 'System', 'ERROR');
    }
}

// ============================================================================
// DEVICE AND STORAGE UTILITIES
// ============================================================================

/**
 * Initialize device ID
 */
function initializeDeviceId() {
    let deviceId = localStorage.getItem('deviceId');
    if (!deviceId) {
        deviceId = 'device-' + Math.random().toString(36).substr(2, 16);
        localStorage.setItem('deviceId', deviceId);
    }
    window.deviceId = deviceId;
    return deviceId;
}

/**
 * Set cookie
 * @param {string} name - Cookie name
 * @param {string} value - Cookie value
 * @param {number} days - Days until expiration
 */
function setCookie(name, value, days) {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/`;
}

/**
 * Escape HTML characters
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Initialize device ID when script loads
document.addEventListener('DOMContentLoaded', function() {
    initializeDeviceId();
});

// Export functions to global scope for backward compatibility
window.LABEL_COUNT = LABEL_COUNT;
window.ROUGHNESS_NAMES = ROUGHNESS_NAMES;
window.formatDutchTime = formatDutchTime;
window.toCESTDateTimeLocal = toCESTDateTimeLocal;
window.fromCESTDateTimeLocal = fromCESTDateTimeLocal;
window.formatShortDateTime = formatShortDateTime;
window.addLog = addLog;
window.addDebug = addDebug;
window.addMessage = addMessage;
window.colorForRoughness = colorForRoughness;
window.directionToCompass = directionToCompass;
window.roughnessLabel = roughnessLabel;
window.roughnessRange = roughnessRange;
window.updateRoughnessLabels = updateRoughnessLabels;
window.filterRoughness = filterRoughness;
window.addFullscreenControl = addFullscreenControl;
window.addPoint = addPoint;
window.authFetch = authFetch;
window.populateDeviceIds = populateDeviceIds;
window.setDateRange = setDateRange;
window.syncRanges = syncRanges;
window.loadLogsPartial = loadLogsPartial;
window.initializeDeviceId = initializeDeviceId;
window.setCookie = setCookie;
window.escapeHtml = escapeHtml;
window.debounce = debounce;
