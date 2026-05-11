const PINKY_CONFIG = {
    baseUrl: 'http://drifter.ddns.net:5000',
    endpoints: {
        health: 'http://drifter.ddns.net:5000/api/health',
        tools: 'http://drifter.ddns.net:5000/api/tools',
        command: 'http://drifter.ddns.net:5000/api/command',
        status: 'http://drifter.ddns.net:5000/api/status',
        confirm: token => `http://drifter.ddns.net:5000/api/confirm/${encodeURIComponent(token)}`
    },
    recommendedApiKey: 'UB$6cv2#p9@YM34%',
    expectedToolCount: 29,
    storageKey: 'rci-pinky-api-key'
};

const pinkyState = {
    latestResponse: null
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
    if (window.location.protocol === 'https:' && PINKY_CONFIG.baseUrl.startsWith('http://')) {
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
        const payload = await pinkyFetch(PINKY_CONFIG.endpoints.health);
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
        const payload = await pinkyFetch(PINKY_CONFIG.endpoints.tools, {
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
        const payload = await pinkyFetch(PINKY_CONFIG.endpoints.status, {
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
        const payload = await pinkyFetch(PINKY_CONFIG.endpoints.command, {
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
        const payload = await pinkyFetch(PINKY_CONFIG.endpoints.confirm(token), {
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
    const rememberedKey = localStorage.getItem(PINKY_CONFIG.storageKey);
    if (rememberedKey) {
        pinkyElement('pinky-api-key').value = rememberedKey;
        pinkyElement('pinky-remember-key').checked = true;
    }
}

function persistPinkyKeyPreference() {
    if (pinkyElement('pinky-remember-key').checked) {
        localStorage.setItem(PINKY_CONFIG.storageKey, getPinkyApiKey());
    } else {
        localStorage.removeItem(PINKY_CONFIG.storageKey);
    }
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
    restorePinkyKey();
    pinkyElement('pinky-health-check').addEventListener('click', checkPinkyHealth);
    pinkyElement('pinky-load-tools').addEventListener('click', loadPinkyTools);
    pinkyElement('pinky-load-status').addEventListener('click', loadPinkyStatus);
    pinkyElement('pinky-command-form').addEventListener('submit', sendPinkyCommand);
    pinkyElement('pinky-confirm-form').addEventListener('submit', confirmPinkyToken);
    pinkyElement('pinky-toggle-key').addEventListener('click', togglePinkyKeyVisibility);
    pinkyElement('pinky-remember-key').addEventListener('change', persistPinkyKeyPreference);
    pinkyElement('pinky-api-key').addEventListener('input', persistPinkyKeyPreference);
    pinkyElement('pinky-copy-response').addEventListener('click', copyPinkyResponse);
    pinkyElement('pinky-clear-command').addEventListener('click', () => {
        pinkyElement('pinky-command-input').value = '';
        pinkyElement('pinky-command-input').focus();
    });

    setPinkyResponse({
        name: 'Pinky Remote Access',
        transport: 'http-json',
        base_url: PINKY_CONFIG.baseUrl,
        expected_tool_count: PINKY_CONFIG.expectedToolCount,
        protected_endpoints_use: 'Authorization: Bearer <api key>'
    });
}

document.addEventListener('DOMContentLoaded', initializePinkyPage);
