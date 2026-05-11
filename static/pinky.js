const DEFAULT_PINKY_SETTINGS = {
    baseUrl: 'http://drifter.ddns.net:5000',
    healthPath: '/api/health',
    toolsPath: '/api/tools',
    commandPath: '/api/command',
    statusPath: '/api/status',
    confirmPath: '/api/confirm/{token}',
    expectedToolCount: 29,
    transport: 'http-json',
    validationStatus: 'Validated ok on 2026-05-11'
};

const PINKY_CONFIG = {
    recommendedApiKey: 'UB$6cv2#p9@YM34%',
    apiKeyStorageKey: 'rci-pinky-api-key',
    settingsStorageKey: 'rci-pinky-settings'
};

const pinkyState = {
    latestResponse: null,
    settings: { ...DEFAULT_PINKY_SETTINGS }
};

function pinkyElement(id) {
    return document.getElementById(id);
}

function setPinkyMessage(message, type = 'success') {
    const status = pinkyElement('pinky-status-message');
    status.textContent = message;
    status.className = `status-message ${type}`;
    status.style.display = 'block';
}

function normalizePinkyBaseUrl(baseUrl) {
    const trimmed = String(baseUrl || '').trim().replace(/\/+$/, '');
    if (!trimmed) return DEFAULT_PINKY_SETTINGS.baseUrl;
    const candidate = /^https?:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;
    try {
        return new URL(candidate).origin;
    } catch (error) {
        return DEFAULT_PINKY_SETTINGS.baseUrl;
    }
}

function normalizePinkyPath(path, fallback) {
    const trimmed = String(path || '').trim();
    if (!trimmed) return fallback;
    if (/^https?:\/\//i.test(trimmed)) return trimmed;
    return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
}

function normalizePinkySettings(settings = {}) {
    const expectedToolCount = Number.parseInt(settings.expectedToolCount, 10);
    return {
        ...DEFAULT_PINKY_SETTINGS,
        ...settings,
        baseUrl: normalizePinkyBaseUrl(settings.baseUrl || DEFAULT_PINKY_SETTINGS.baseUrl),
        healthPath: normalizePinkyPath(settings.healthPath, DEFAULT_PINKY_SETTINGS.healthPath),
        toolsPath: normalizePinkyPath(settings.toolsPath, DEFAULT_PINKY_SETTINGS.toolsPath),
        commandPath: normalizePinkyPath(settings.commandPath, DEFAULT_PINKY_SETTINGS.commandPath),
        statusPath: normalizePinkyPath(settings.statusPath, DEFAULT_PINKY_SETTINGS.statusPath),
        confirmPath: normalizePinkyPath(settings.confirmPath, DEFAULT_PINKY_SETTINGS.confirmPath),
        expectedToolCount: Number.isFinite(expectedToolCount) && expectedToolCount >= 0 ? expectedToolCount : DEFAULT_PINKY_SETTINGS.expectedToolCount
    };
}

function buildPinkyUrl(path) {
    const settings = pinkyState.settings;
    if (/^https?:\/\//i.test(path)) return path;
    const baseUrl = settings.baseUrl.endsWith('/') ? settings.baseUrl : `${settings.baseUrl}/`;
    try {
        return new URL(path.replace(/^\/+/, ''), baseUrl).toString();
    } catch (error) {
        return new URL(path.replace(/^\/+/, ''), `${DEFAULT_PINKY_SETTINGS.baseUrl}/`).toString();
    }
}

function getPinkyEndpoints() {
    const settings = pinkyState.settings;
    return {
        health: buildPinkyUrl(settings.healthPath),
        tools: buildPinkyUrl(settings.toolsPath),
        command: buildPinkyUrl(settings.commandPath),
        status: buildPinkyUrl(settings.statusPath),
        confirm: token => buildPinkyUrl(settings.confirmPath.replace('{token}', encodeURIComponent(token)))
    };
}

function getPinkyApiKey() {
    return pinkyElement('pinky-api-key').value.trim();
}

function getPinkyHeaders(includeJson = false) {
    const apiKey = getPinkyApiKey();
    const headers = {};
    if (apiKey) {
        headers.Authorization = `Bearer ${apiKey}`;
    }
    if (includeJson) {
        headers['Content-Type'] = 'application/json';
    }
    return headers;
}

function prettyJson(value) {
    return JSON.stringify(value, null, 2);
}

function setPinkyResponse(value) {
    pinkyState.latestResponse = value;
    pinkyElement('pinky-response-output').textContent = typeof value === 'string' ? value : prettyJson(value);
}

function describeFetchError(error) {
    if (window.location.protocol === 'https:' && pinkyState.settings.baseUrl.startsWith('http://')) {
        return `${error.message}. This page is using HTTPS while Pinky is exposed over HTTP, so the browser may block mixed-content requests.`;
    }
    return `${error.message}. Check that Pinky is reachable and allows browser CORS requests from this site.`;
}

async function pinkyFetch(url, options = {}) {
    const response = await fetch(url, options);
    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) {
        const message = typeof payload === 'string' ? payload : (payload.detail || payload.message || prettyJson(payload));
        throw new Error(`HTTP ${response.status}: ${message}`);
    }
    return payload;
}

async function checkPinkyHealth() {
    try {
        setPinkyMessage('Checking Pinky health...', 'warning');
        const payload = await pinkyFetch(getPinkyEndpoints().health);
        setPinkyResponse(payload);
        const healthStatus = payload.status || payload.health_status || 'ok';
        pinkyElement('pinky-health-pill').textContent = `Health ${healthStatus}`;
        pinkyElement('pinky-health-pill').className = 'pill success';
        setPinkyMessage('Pinky health check completed.', 'success');
    } catch (error) {
        pinkyElement('pinky-health-pill').textContent = 'Health unavailable';
        pinkyElement('pinky-health-pill').className = 'pill muted';
        setPinkyResponse({ error: describeFetchError(error) });
        setPinkyMessage(describeFetchError(error), 'error');
    }
}

function normalizePinkyTools(payload) {
    if (Array.isArray(payload)) return payload;
    if (payload && Array.isArray(payload.tools)) return payload.tools;
    if (payload && payload.data && Array.isArray(payload.data.tools)) return payload.data.tools;
    return [];
}

function renderPinkyTools(tools) {
    const container = pinkyElement('pinky-tools-list');
    container.innerHTML = '';
    if (!tools.length) {
        container.textContent = 'No tools were returned by Pinky.';
        pinkyElement('pinky-tools-summary').textContent = '0 tools';
        return;
    }

    tools.forEach(tool => {
        const card = document.createElement('article');
        card.className = 'ai-tool-card';
        const title = document.createElement('h5');
        title.textContent = tool.name || tool.id || 'Unnamed tool';
        const description = document.createElement('p');
        description.textContent = tool.description || tool.summary || 'No description provided.';
        const metadata = document.createElement('small');
        metadata.textContent = tool.server || tool.category || tool.input_schema ? prettyJson(tool.input_schema || tool.parameters || tool) : '';
        card.append(title, description);
        if (metadata.textContent) card.appendChild(metadata);
        container.appendChild(card);
    });

    pinkyElement('pinky-tools-summary').textContent = `${tools.length} tools loaded`;
    pinkyElement('pinky-tool-count-pill').textContent = `${tools.length} tools available`;
}

async function loadPinkyTools() {
    try {
        setPinkyMessage('Loading Pinky tools...', 'warning');
        const payload = await pinkyFetch(getPinkyEndpoints().tools, {
            headers: getPinkyHeaders()
        });
        const tools = normalizePinkyTools(payload);
        renderPinkyTools(tools);
        setPinkyResponse(payload);
        setPinkyMessage('Pinky tools loaded.', 'success');
    } catch (error) {
        setPinkyResponse({ error: describeFetchError(error) });
        setPinkyMessage(describeFetchError(error), 'error');
    }
}

async function loadPinkyStatus() {
    try {
        setPinkyMessage('Loading Pinky status...', 'warning');
        const payload = await pinkyFetch(getPinkyEndpoints().status, {
            headers: getPinkyHeaders()
        });
        setPinkyResponse(payload);
        setPinkyMessage('Pinky status loaded.', 'success');
    } catch (error) {
        setPinkyResponse({ error: describeFetchError(error) });
        setPinkyMessage(describeFetchError(error), 'error');
    }
}

async function sendPinkyCommand(event) {
    event.preventDefault();
    const commandInput = pinkyElement('pinky-command-input');
    const command = commandInput.value.trim();
    if (!command) {
        setPinkyMessage('Enter a command before sending it to Pinky.', 'error');
        commandInput.focus();
        return;
    }

    try {
        pinkyElement('pinky-send-command').disabled = true;
        setPinkyMessage('Sending command to Pinky...', 'warning');
        const payload = await pinkyFetch(getPinkyEndpoints().command, {
            method: 'POST',
            headers: getPinkyHeaders(true),
            body: JSON.stringify({ command })
        });
        setPinkyResponse(payload);
        setPinkyMessage('Pinky command completed.', 'success');
    } catch (error) {
        setPinkyResponse({ error: describeFetchError(error) });
        setPinkyMessage(describeFetchError(error), 'error');
    } finally {
        pinkyElement('pinky-send-command').disabled = false;
    }
}

async function confirmPinkyToken(event) {
    event.preventDefault();
    const tokenInput = pinkyElement('pinky-confirm-token');
    const token = tokenInput.value.trim();
    if (!token) {
        setPinkyMessage('Paste a confirmation token before confirming.', 'error');
        tokenInput.focus();
        return;
    }

    try {
        setPinkyMessage('Confirming Pinky token...', 'warning');
        const payload = await pinkyFetch(getPinkyEndpoints().confirm(token), {
            method: 'POST',
            headers: getPinkyHeaders()
        });
        setPinkyResponse(payload);
        setPinkyMessage('Pinky confirmation completed.', 'success');
    } catch (error) {
        setPinkyResponse({ error: describeFetchError(error) });
        setPinkyMessage(describeFetchError(error), 'error');
    }
}

function restorePinkyKey() {
    const rememberedKey = localStorage.getItem(PINKY_CONFIG.apiKeyStorageKey);
    if (rememberedKey) {
        pinkyElement('pinky-api-key').value = rememberedKey;
        pinkyElement('pinky-remember-key').checked = true;
    }
}

function persistPinkyKeyPreference() {
    if (pinkyElement('pinky-remember-key').checked) {
        localStorage.setItem(PINKY_CONFIG.apiKeyStorageKey, getPinkyApiKey());
    } else {
        localStorage.removeItem(PINKY_CONFIG.apiKeyStorageKey);
    }
}

function getPinkySettingsFromForm() {
    return normalizePinkySettings({
        baseUrl: pinkyElement('pinky-base-url').value,
        healthPath: pinkyElement('pinky-health-path').value,
        toolsPath: pinkyElement('pinky-tools-path').value,
        commandPath: pinkyElement('pinky-command-path').value,
        statusPath: pinkyElement('pinky-status-path').value,
        confirmPath: pinkyElement('pinky-confirm-path').value,
        expectedToolCount: pinkyElement('pinky-expected-tools').value
    });
}

function applyPinkySettings(settings) {
    pinkyState.settings = normalizePinkySettings(settings);
    pinkyElement('pinky-base-url').value = pinkyState.settings.baseUrl;
    pinkyElement('pinky-health-path').value = pinkyState.settings.healthPath;
    pinkyElement('pinky-tools-path').value = pinkyState.settings.toolsPath;
    pinkyElement('pinky-command-path').value = pinkyState.settings.commandPath;
    pinkyElement('pinky-status-path').value = pinkyState.settings.statusPath;
    pinkyElement('pinky-confirm-path').value = pinkyState.settings.confirmPath;
    pinkyElement('pinky-expected-tools').value = pinkyState.settings.expectedToolCount;
    updatePinkyEndpointSummary();
}

function persistPinkySettings(showMessage = true) {
    const settings = getPinkySettingsFromForm();
    applyPinkySettings(settings);
    localStorage.setItem(PINKY_CONFIG.settingsStorageKey, JSON.stringify(pinkyState.settings));
    if (showMessage) {
        setPinkyMessage('Pinky settings saved in this browser.', 'success');
    }
}

function restorePinkySettings() {
    const rememberedSettings = localStorage.getItem(PINKY_CONFIG.settingsStorageKey);
    if (!rememberedSettings) {
        applyPinkySettings(DEFAULT_PINKY_SETTINGS);
        return;
    }

    try {
        applyPinkySettings(JSON.parse(rememberedSettings));
    } catch (error) {
        applyPinkySettings(DEFAULT_PINKY_SETTINGS);
        localStorage.removeItem(PINKY_CONFIG.settingsStorageKey);
        setPinkyMessage(`Saved Pinky settings could not be loaded: ${error.message}`, 'error');
    }
}

function resetPinkySettings() {
    localStorage.removeItem(PINKY_CONFIG.settingsStorageKey);
    applyPinkySettings(DEFAULT_PINKY_SETTINGS);
    setPinkyMessage('Pinky settings reset to defaults.', 'success');
}

function updatePinkyEndpointSummary() {
    const endpoints = getPinkyEndpoints();
    const baseUrlLink = pinkyElement('pinky-base-url-link');
    baseUrlLink.href = pinkyState.settings.baseUrl;
    baseUrlLink.textContent = pinkyState.settings.baseUrl;
    pinkyElement('pinky-transport-label').textContent = pinkyState.settings.transport;
    pinkyElement('pinky-validation-label').textContent = pinkyState.settings.validationStatus;
    pinkyElement('pinky-openapi-link').href = buildPinkyUrl('/openapi.json');
    pinkyElement('pinky-manifest-link').href = buildPinkyUrl('/.well-known/omi-tools.json');
    pinkyElement('pinky-tool-count-pill').textContent = `${pinkyState.settings.expectedToolCount} tools expected`;
    setPinkyResponse({
        name: 'Pinky Remote Access',
        transport: pinkyState.settings.transport,
        base_url: pinkyState.settings.baseUrl,
        endpoints,
        expected_tool_count: pinkyState.settings.expectedToolCount,
        protected_endpoints_use: 'Authorization: Bearer <api key>'
    });
}

function togglePinkyKeyVisibility() {
    const input = pinkyElement('pinky-api-key');
    const button = pinkyElement('pinky-toggle-key');
    const showing = input.type === 'text';
    input.type = showing ? 'password' : 'text';
    button.textContent = showing ? 'Show' : 'Hide';
    button.setAttribute('aria-pressed', String(!showing));
}

async function copyPinkyResponse() {
    const content = pinkyElement('pinky-response-output').textContent;
    try {
        await navigator.clipboard.writeText(content);
        setPinkyMessage('Copied the latest Pinky response to the clipboard.', 'success');
    } catch (error) {
        setPinkyMessage(`Could not copy response: ${error.message}`, 'error');
    }
}

function initializePinkyPage() {
    restorePinkySettings();
    restorePinkyKey();
    pinkyElement('pinky-health-check').addEventListener('click', checkPinkyHealth);
    pinkyElement('pinky-load-tools').addEventListener('click', loadPinkyTools);
    pinkyElement('pinky-load-status').addEventListener('click', loadPinkyStatus);
    pinkyElement('pinky-command-form').addEventListener('submit', sendPinkyCommand);
    pinkyElement('pinky-confirm-form').addEventListener('submit', confirmPinkyToken);
    pinkyElement('pinky-toggle-key').addEventListener('click', togglePinkyKeyVisibility);
    pinkyElement('pinky-remember-key').addEventListener('change', persistPinkyKeyPreference);
    pinkyElement('pinky-api-key').addEventListener('input', persistPinkyKeyPreference);
    pinkyElement('pinky-save-settings').addEventListener('click', () => persistPinkySettings());
    pinkyElement('pinky-reset-settings').addEventListener('click', resetPinkySettings);
    pinkyElement('pinky-settings-form').addEventListener('input', () => {
        applyPinkySettings(getPinkySettingsFromForm());
    });
    pinkyElement('pinky-settings-form').addEventListener('submit', event => {
        event.preventDefault();
        persistPinkySettings();
    });
    pinkyElement('pinky-copy-response').addEventListener('click', copyPinkyResponse);
    pinkyElement('pinky-clear-command').addEventListener('click', () => {
        pinkyElement('pinky-command-input').value = '';
        pinkyElement('pinky-command-input').focus();
    });
}

document.addEventListener('DOMContentLoaded', initializePinkyPage);
