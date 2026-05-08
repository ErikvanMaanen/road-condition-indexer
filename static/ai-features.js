(function () {
    const STORAGE_KEY = 'rci.ai.omiMcpConfig';
    const DEFAULT_CONFIG = {
        enabled: false,
        displayName: 'Omi',
        serverKey: 'omi',
        url: 'https://api.omi.me/v1/mcp/sse',
        vscodeType: 'sse',
        transport: 'streamable_http',
        token: '',
        notes: ''
    };

    const elements = {};

    function getElement(id) {
        return document.getElementById(id);
    }

    function loadSavedConfig() {
        let raw = '';
        try {
            raw = localStorage.getItem(STORAGE_KEY);
        } catch (error) {
            console.warn('Unable to read saved Omi MCP config. Falling back to defaults.', error);
            return { ...DEFAULT_CONFIG };
        }
        if (!raw) return { ...DEFAULT_CONFIG };
        try {
            const parsed = JSON.parse(raw);
            return { ...DEFAULT_CONFIG, ...parsed };
        } catch (error) {
            console.warn('Invalid saved Omi MCP config. Falling back to defaults.', error);
            return { ...DEFAULT_CONFIG };
        }
    }

    function readFormConfig() {
        return {
            enabled: elements.enabled.checked,
            displayName: elements.displayName.value.trim() || DEFAULT_CONFIG.displayName,
            serverKey: elements.serverKey.value.trim() || DEFAULT_CONFIG.serverKey,
            url: elements.url.value.trim() || DEFAULT_CONFIG.url,
            vscodeType: elements.vscodeType.value,
            transport: elements.transport.value,
            token: elements.token.value.trim(),
            notes: elements.notes.value.trim()
        };
    }

    function applyConfig(config) {
        elements.enabled.checked = Boolean(config.enabled);
        elements.displayName.value = config.displayName;
        elements.serverKey.value = config.serverKey;
        elements.url.value = config.url;
        elements.vscodeType.value = config.vscodeType;
        elements.transport.value = config.transport;
        elements.token.value = config.token;
        elements.notes.value = config.notes;
        renderSnippets();
    }

    function getSnippetToken(config) {
        if (elements.includeToken.checked && config.token) {
            return config.token;
        }
        return '<key>';
    }

    function buildVsCodeSnippet(config) {
        const token = getSnippetToken(config);
        const serverKey = config.serverKey || DEFAULT_CONFIG.serverKey;
        return JSON.stringify({
            servers: {
                [serverKey]: {
                    type: config.vscodeType,
                    url: config.url,
                    headers: {
                        Authorization: `Bearer ${token}`
                    }
                }
            }
        }, null, 2);
    }

    function buildPythonSnippet(config) {
        const token = getSnippetToken(config) === '<key>' ? 'omi_mcp_YOUR_KEY' : config.token;
        const serverKey = config.serverKey || DEFAULT_CONFIG.serverKey;
        return `from langchain_mcp_adapters.client import MultiServerMCPClient\n\nasync with MultiServerMCPClient({\n    "${serverKey}": {\n        "url": "${config.url}",\n        "transport": "${config.transport}",\n        "headers": {"Authorization": "Bearer ${token}"},\n    }\n}) as client:\n    tools = client.get_tools()\n    result = await client.call_tool("${serverKey}", "search_memories", {\n        "query": "morning routine",\n        "limit": 5,\n    })`;
    }

    function renderSnippets() {
        const config = readFormConfig();
        elements.vscodeSnippet.textContent = buildVsCodeSnippet(config);
        elements.pythonSnippet.textContent = buildPythonSnippet(config);
    }

    function showStatus(message, type) {
        elements.status.textContent = message;
        elements.status.className = `status-message ${type || ''}`.trim();
    }

    function validateConfig(config) {
        if (!config.url.startsWith('https://')) {
            return 'MCP URL should use HTTPS.';
        }
        if (config.token && !config.token.startsWith('omi_mcp_')) {
            return 'Omi MCP tokens should start with omi_mcp_.';
        }
        if (!/^[a-zA-Z0-9_-]+$/.test(config.serverKey)) {
            return 'Server key can contain letters, numbers, underscores, and hyphens only.';
        }
        return '';
    }

    function saveConfig(event) {
        event.preventDefault();
        const config = readFormConfig();
        const validationError = validateConfig(config);
        if (validationError) {
            showStatus(validationError, 'error');
            return;
        }
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
        } catch (error) {
            console.warn('Unable to save Omi MCP config.', error);
            showStatus('Unable to save settings in this browser.', 'error');
            return;
        }
        renderSnippets();
        showStatus('Omi MCP settings saved in this browser.', 'success');
    }

    function resetDefaults() {
        applyConfig({ ...DEFAULT_CONFIG });
        showStatus('Omi MCP settings reset to defaults. Save to keep these values.', 'warning');
    }

    function clearSavedConfig() {
        try {
            localStorage.removeItem(STORAGE_KEY);
        } catch (error) {
            console.warn('Unable to clear saved Omi MCP config.', error);
            showStatus('Unable to clear saved settings in this browser.', 'error');
            return;
        }
        applyConfig({ ...DEFAULT_CONFIG });
        showStatus('Saved Omi MCP settings cleared from this browser.', 'success');
    }

    async function copyText(text, successMessage) {
        if (!navigator.clipboard) {
            showStatus('Clipboard access is not available in this browser.', 'error');
            return;
        }
        try {
            await navigator.clipboard.writeText(text);
            showStatus(successMessage, 'success');
        } catch (error) {
            console.warn('Unable to copy AI config snippet.', error);
            showStatus('Unable to copy snippet to the clipboard.', 'error');
        }
    }

    function toggleTokenVisibility() {
        const showing = elements.token.type === 'text';
        elements.token.type = showing ? 'password' : 'text';
        elements.toggleToken.textContent = showing ? 'Show' : 'Hide';
    }

    function bindElements() {
        elements.form = getElement('omi-mcp-form');
        elements.enabled = getElement('omi-enabled');
        elements.displayName = getElement('omi-display-name');
        elements.serverKey = getElement('omi-server-key');
        elements.url = getElement('omi-url');
        elements.vscodeType = getElement('omi-vscode-type');
        elements.transport = getElement('omi-transport');
        elements.token = getElement('omi-token');
        elements.notes = getElement('omi-notes');
        elements.status = getElement('omi-status');
        elements.reset = getElement('omi-reset');
        elements.clear = getElement('omi-clear');
        elements.includeToken = getElement('omi-include-token');
        elements.vscodeSnippet = getElement('omi-vscode-snippet');
        elements.pythonSnippet = getElement('omi-python-snippet');
        elements.copyVsCode = getElement('omi-copy-vscode');
        elements.copyPython = getElement('omi-copy-python');
        elements.toggleToken = getElement('omi-toggle-token');
    }

    function bindEvents() {
        elements.form.addEventListener('submit', saveConfig);
        elements.reset.addEventListener('click', resetDefaults);
        elements.clear.addEventListener('click', clearSavedConfig);
        elements.toggleToken.addEventListener('click', toggleTokenVisibility);
        elements.includeToken.addEventListener('change', renderSnippets);

        [
            elements.enabled,
            elements.displayName,
            elements.serverKey,
            elements.url,
            elements.vscodeType,
            elements.transport,
            elements.token,
            elements.notes
        ].forEach(element => {
            element.addEventListener('input', renderSnippets);
            element.addEventListener('change', renderSnippets);
        });

        elements.copyVsCode.addEventListener('click', () => copyText(elements.vscodeSnippet.textContent, 'VS Code MCP config copied.'));
        elements.copyPython.addEventListener('click', () => copyText(elements.pythonSnippet.textContent, 'Python SDK example copied.'));
    }

    document.addEventListener('DOMContentLoaded', () => {
        bindElements();
        bindEvents();
        applyConfig(loadSavedConfig());
    });
})();
