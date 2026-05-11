(function () {
    const STORAGE_KEY = 'rci.ai.workspaceConfig.v1';
    const LEGACY_OMI_KEY = 'rci.ai.omiMcpConfig';

    const DEFAULT_AGENT = {
        id: 'agent-road-analyst',
        enabled: true,
        name: 'Road Analyst Agent',
        provider: 'OpenAI / local workflow',
        key: 'road_analyst',
        runtime: 'Configured in client',
        tools: 'Read logs, inspect road-condition data, use enabled MCP services',
        instructions: 'Review the current road-condition context, identify anomalies, and return concise operational next steps.',
        notes: 'Default starter profile. Update it for the assistant or IDE agent you want to use.',
        testScenario: 'Investigate today\'s newest road-condition anomaly and summarize likely cause, confidence, and next actions.'
    };

    const DEFAULT_MCP = {
        id: 'mcp-omi',
        enabled: true,
        name: 'Omi',
        key: 'omi',
        url: 'https://api.omi.me/v1/mcp/sse',
        vscodeType: 'sse',
        transport: 'streamable_http',
        token: '',
        notes: 'Create a key in the Omi app under Settings → Developer → MCP.'
    };

    const state = {
        agents: [],
        mcps: [],
        selectedAgentId: '',
        selectedMcpId: ''
    };

    const elements = {};
    let discoveredTools = [];

    function $(id) {
        return document.getElementById(id);
    }

    function clone(value) {
        return JSON.parse(JSON.stringify(value));
    }

    function slugify(value, fallback) {
        const slug = String(value || '')
            .toLowerCase()
            .replace(/[^a-z0-9_-]+/g, '_')
            .replace(/^_+|_+$/g, '')
            .slice(0, 50);
        return slug || fallback;
    }

    function uniqueId(prefix) {
        if (window.crypto && typeof window.crypto.randomUUID === 'function') {
            return `${prefix}-${window.crypto.randomUUID()}`;
        }
        return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    }

    function defaultWorkspace() {
        return {
            agents: [clone(DEFAULT_AGENT)],
            mcps: [clone(DEFAULT_MCP)],
            selectedAgentId: DEFAULT_AGENT.id,
            selectedMcpId: DEFAULT_MCP.id
        };
    }

    function migrateLegacyOmi(workspace) {
        try {
            const raw = localStorage.getItem(LEGACY_OMI_KEY);
            if (!raw || workspace.mcps.length) return workspace;
            const legacy = JSON.parse(raw);
            const omi = {
                ...clone(DEFAULT_MCP),
                enabled: Boolean(legacy.enabled),
                name: legacy.displayName || DEFAULT_MCP.name,
                key: legacy.serverKey || DEFAULT_MCP.key,
                url: legacy.url || DEFAULT_MCP.url,
                vscodeType: legacy.vscodeType || DEFAULT_MCP.vscodeType,
                transport: legacy.transport || DEFAULT_MCP.transport,
                token: legacy.token || '',
                notes: legacy.notes || DEFAULT_MCP.notes
            };
            workspace.mcps = [omi];
            workspace.selectedMcpId = omi.id;
        } catch (error) {
            console.warn('Unable to migrate legacy Omi MCP config.', error);
        }
        return workspace;
    }

    function normalizeWorkspace(workspace) {
        const defaults = defaultWorkspace();
        const normalized = {
            agents: Array.isArray(workspace.agents) ? workspace.agents : defaults.agents,
            mcps: Array.isArray(workspace.mcps) ? workspace.mcps : defaults.mcps,
            selectedAgentId: workspace.selectedAgentId || '',
            selectedMcpId: workspace.selectedMcpId || ''
        };
        if (!normalized.agents.length) normalized.agents = defaults.agents;
        if (!normalized.mcps.length) normalized.mcps = defaults.mcps;
        normalized.selectedAgentId = normalized.agents.some(agent => agent.id === normalized.selectedAgentId)
            ? normalized.selectedAgentId
            : normalized.agents[0].id;
        normalized.selectedMcpId = normalized.mcps.some(mcp => mcp.id === normalized.selectedMcpId)
            ? normalized.selectedMcpId
            : normalized.mcps[0].id;
        return normalized;
    }

    function loadWorkspace() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return migrateLegacyOmi(defaultWorkspace());
            return normalizeWorkspace(JSON.parse(raw));
        } catch (error) {
            console.warn('Unable to read saved AI workspace config. Falling back to defaults.', error);
            return defaultWorkspace();
        }
    }

    function saveWorkspace() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                agents: state.agents,
                mcps: state.mcps,
                selectedAgentId: state.selectedAgentId,
                selectedMcpId: state.selectedMcpId
            }));
            return true;
        } catch (error) {
            console.warn('Unable to save AI workspace config.', error);
            return false;
        }
    }

    function selectedAgent() {
        return state.agents.find(agent => agent.id === state.selectedAgentId) || state.agents[0];
    }

    function selectedMcp() {
        return state.mcps.find(mcp => mcp.id === state.selectedMcpId) || state.mcps[0];
    }

    function setStatus(element, message, type) {
        element.textContent = message;
        element.className = `status-message ${type || ''}`.trim();
    }

    function renderSummary() {
        const enabledAgents = state.agents.filter(agent => agent.enabled).length;
        const enabledMcps = state.mcps.filter(mcp => mcp.enabled).length;
        elements.agentSummaryPill.textContent = `🤖 ${state.agents.length} agent${state.agents.length === 1 ? '' : 's'}`;
        elements.mcpSummaryPill.textContent = `🔌 ${state.mcps.length} MCP service${state.mcps.length === 1 ? '' : 's'}`;
        elements.enabledSummaryPill.textContent = `✅ ${enabledAgents + enabledMcps} enabled`;
        elements.agentOverviewText.textContent = `${enabledAgents} enabled of ${state.agents.length}. Create profiles for IDE assistants, local workflow runners, hosted copilots, or custom automations.`;
        elements.mcpOverviewText.textContent = `${enabledMcps} enabled of ${state.mcps.length}. Manage service URLs, transports, auth headers, snippets, and live tool tests.`;
    }

    function configButton(config, selectedId, type) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `ai-config-item${config.id === selectedId ? ' selected' : ''}`;
        button.setAttribute('role', 'option');
        button.setAttribute('aria-selected', config.id === selectedId ? 'true' : 'false');
        button.dataset.id = config.id;
        button.dataset.type = type;
        button.innerHTML = `
            <span class="ai-config-item-main">
                <strong>${escapeHtml(config.name || config.key || 'Untitled')}</strong>
                <small>${escapeHtml(config.provider || config.url || config.runtime || 'No endpoint')}</small>
            </span>
            <span class="pill ${config.enabled ? 'success' : 'muted'}">${config.enabled ? 'Enabled' : 'Disabled'}</span>
        `;
        return button;
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>'"]/g, character => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[character]));
    }

    function renderLists() {
        elements.agentList.innerHTML = '';
        state.agents.forEach(agent => elements.agentList.appendChild(configButton(agent, state.selectedAgentId, 'agent')));
        elements.mcpList.innerHTML = '';
        state.mcps.forEach(mcp => elements.mcpList.appendChild(configButton(mcp, state.selectedMcpId, 'mcp')));
    }

    function applyAgentToForm() {
        const agent = selectedAgent();
        elements.agentEnabled.checked = Boolean(agent.enabled);
        elements.agentName.value = agent.name || '';
        elements.agentProvider.value = agent.provider || '';
        elements.agentKey.value = agent.key || '';
        elements.agentRuntime.value = agent.runtime || '';
        elements.agentTools.value = agent.tools || '';
        elements.agentInstructions.value = agent.instructions || '';
        elements.agentNotes.value = agent.notes || '';
        elements.agentTestScenario.value = agent.testScenario || '';
        elements.selectedAgentPill.textContent = agent.name || 'Agent selected';
        elements.deleteAgent.disabled = state.agents.length <= 1;
    }

    function applyMcpToForm() {
        const mcp = selectedMcp();
        elements.mcpEnabled.checked = Boolean(mcp.enabled);
        elements.mcpName.value = mcp.name || '';
        elements.mcpKey.value = mcp.key || '';
        elements.mcpUrl.value = mcp.url || '';
        elements.mcpVsCodeType.value = mcp.vscodeType || DEFAULT_MCP.vscodeType;
        elements.mcpTransport.value = mcp.transport || DEFAULT_MCP.transport;
        elements.mcpToken.value = mcp.token || '';
        elements.mcpNotes.value = mcp.notes || '';
        elements.selectedMcpPill.textContent = mcp.name || 'MCP selected';
        elements.deleteMcp.disabled = state.mcps.length <= 1;
        discoveredTools = [];
        renderToolList([]);
        renderSnippets();
    }

    function renderAll() {
        renderSummary();
        renderLists();
        applyAgentToForm();
        applyMcpToForm();
    }

    function readAgentForm() {
        return {
            ...selectedAgent(),
            enabled: elements.agentEnabled.checked,
            name: elements.agentName.value.trim(),
            provider: elements.agentProvider.value.trim(),
            key: slugify(elements.agentKey.value, 'agent'),
            runtime: elements.agentRuntime.value.trim(),
            tools: elements.agentTools.value.trim(),
            instructions: elements.agentInstructions.value.trim(),
            notes: elements.agentNotes.value.trim(),
            testScenario: elements.agentTestScenario.value.trim()
        };
    }

    function readMcpForm() {
        return {
            ...selectedMcp(),
            enabled: elements.mcpEnabled.checked,
            name: elements.mcpName.value.trim(),
            key: slugify(elements.mcpKey.value, 'mcp'),
            url: elements.mcpUrl.value.trim(),
            vscodeType: elements.mcpVsCodeType.value,
            transport: elements.mcpTransport.value,
            token: elements.mcpToken.value.trim(),
            notes: elements.mcpNotes.value.trim()
        };
    }

    function validateKey(key, label) {
        if (!/^[a-zA-Z0-9_-]+$/.test(key)) return `${label} key can contain letters, numbers, underscores, and hyphens only.`;
        return '';
    }

    function validateMcp(config) {
        const keyError = validateKey(config.key, 'MCP server');
        if (keyError) return keyError;
        if (!config.name) return 'MCP display name is required.';
        if (!config.url) return 'MCP URL is required.';
        if (!/^https?:\/\//i.test(config.url)) return 'MCP URL should start with http:// or https://.';
        return '';
    }

    function validateAgent(config) {
        const keyError = validateKey(config.key, 'Agent');
        if (keyError) return keyError;
        if (!config.name) return 'Agent display name is required.';
        return '';
    }

    function updateSelectedAgent(config) {
        state.agents = state.agents.map(agent => agent.id === state.selectedAgentId ? config : agent);
    }

    function updateSelectedMcp(config) {
        state.mcps = state.mcps.map(mcp => mcp.id === state.selectedMcpId ? config : mcp);
    }

    function saveAgent(event) {
        event.preventDefault();
        const config = readAgentForm();
        const validationError = validateAgent(config);
        if (validationError) {
            setStatus(elements.agentStatus, validationError, 'error');
            return;
        }
        updateSelectedAgent(config);
        if (!saveWorkspace()) {
            setStatus(elements.agentStatus, 'Unable to save agent settings in this browser.', 'error');
            return;
        }
        renderSummary();
        renderLists();
        applyAgentToForm();
        setStatus(elements.agentStatus, `${config.name} saved.`, 'success');
    }

    function saveMcp(event) {
        event.preventDefault();
        const config = readMcpForm();
        const validationError = validateMcp(config);
        if (validationError) {
            setStatus(elements.mcpStatus, validationError, 'error');
            return;
        }
        updateSelectedMcp(config);
        if (!saveWorkspace()) {
            setStatus(elements.mcpStatus, 'Unable to save MCP settings in this browser.', 'error');
            return;
        }
        renderSummary();
        renderLists();
        applyMcpToForm();
        setStatus(elements.mcpStatus, `${config.name} saved.`, 'success');
    }

    function addAgent() {
        const id = uniqueId('agent');
        const agent = {
            ...clone(DEFAULT_AGENT),
            id,
            enabled: false,
            name: 'New Agent',
            key: slugify(`agent_${state.agents.length + 1}`, 'agent')
        };
        state.agents.push(agent);
        state.selectedAgentId = id;
        saveWorkspace();
        renderAll();
        setStatus(elements.agentStatus, 'New agent created. Update and save its configuration.', 'warning');
    }

    function addMcp() {
        const id = uniqueId('mcp');
        const mcp = {
            ...clone(DEFAULT_MCP),
            id,
            enabled: false,
            name: 'New MCP Service',
            key: slugify(`mcp_${state.mcps.length + 1}`, 'mcp'),
            url: 'https://example.com/mcp'
        };
        state.mcps.push(mcp);
        state.selectedMcpId = id;
        saveWorkspace();
        renderAll();
        setStatus(elements.mcpStatus, 'New MCP service created. Update and save its configuration.', 'warning');
    }

    function deleteSelectedAgent() {
        if (state.agents.length <= 1) return;
        const removed = selectedAgent();
        state.agents = state.agents.filter(agent => agent.id !== state.selectedAgentId);
        state.selectedAgentId = state.agents[0].id;
        saveWorkspace();
        renderAll();
        setStatus(elements.agentStatus, `${removed.name} removed.`, 'success');
    }

    function deleteSelectedMcp() {
        if (state.mcps.length <= 1) return;
        const removed = selectedMcp();
        state.mcps = state.mcps.filter(mcp => mcp.id !== state.selectedMcpId);
        state.selectedMcpId = state.mcps[0].id;
        saveWorkspace();
        renderAll();
        setStatus(elements.mcpStatus, `${removed.name} removed.`, 'success');
    }

    function resetAll() {
        const fresh = defaultWorkspace();
        state.agents = fresh.agents;
        state.mcps = fresh.mcps;
        state.selectedAgentId = fresh.selectedAgentId;
        state.selectedMcpId = fresh.selectedMcpId;
        saveWorkspace();
        renderAll();
        setStatus(elements.agentStatus, 'AI workspace reset to defaults.', 'warning');
        setStatus(elements.mcpStatus, 'AI workspace reset to defaults.', 'warning');
    }

    function selectConfig(event) {
        const button = event.target.closest('.ai-config-item');
        if (!button) return;
        if (button.dataset.type === 'agent') {
            state.selectedAgentId = button.dataset.id;
            applyAgentToForm();
            renderLists();
            setStatus(elements.agentStatus, '', '');
        } else {
            state.selectedMcpId = button.dataset.id;
            applyMcpToForm();
            renderLists();
            setStatus(elements.mcpStatus, '', '');
            setStatus(elements.mcpTestStatus, '', '');
            elements.testResult.textContent = '';
        }
        saveWorkspace();
    }

    function getSnippetToken(config) {
        if (elements.mcpIncludeToken.checked && config.token) return config.token;
        return '<key>';
    }

    function buildVsCodeSnippet(config) {
        const token = getSnippetToken(config);
        const server = {
            type: config.vscodeType,
            url: config.url
        };
        if (config.token || elements.mcpIncludeToken.checked) {
            server.headers = { Authorization: `Bearer ${token}` };
        }
        return JSON.stringify({ servers: { [config.key || DEFAULT_MCP.key]: server } }, null, 2);
    }

    function buildPythonSnippet(config) {
        const token = getSnippetToken(config) === '<key>' ? 'YOUR_MCP_TOKEN' : config.token;
        const headersLine = config.token || elements.mcpIncludeToken.checked
            ? `,\n        "headers": {"Authorization": "Bearer ${token}"}`
            : '';
        return `from langchain_mcp_adapters.client import MultiServerMCPClient\n\nasync with MultiServerMCPClient({\n    "${config.key}": {\n        "url": "${config.url}",\n        "transport": "${config.transport}"${headersLine},\n    }\n}) as client:\n    tools = client.get_tools()\n    # result = await client.call_tool("${config.key}", "tool_name", {"example": "value"})`;
    }

    function renderSnippets() {
        const config = readMcpForm();
        elements.vscodeSnippet.textContent = buildVsCodeSnippet(config);
        elements.pythonSnippet.textContent = buildPythonSnippet(config);
    }

    async function copyText(text, successMessage, statusTarget) {
        if (!text) {
            statusTarget('Nothing to copy yet.', 'warning');
            return;
        }
        try {
            await navigator.clipboard.writeText(text);
            statusTarget(successMessage, 'success');
        } catch (error) {
            console.warn('Clipboard copy failed.', error);
            statusTarget('Copy failed. Select the text manually.', 'error');
        }
    }

    function toggleTokenVisibility() {
        const isHidden = elements.mcpToken.type === 'password';
        elements.mcpToken.type = isHidden ? 'text' : 'password';
        elements.mcpToggleToken.textContent = isHidden ? 'Hide' : 'Show';
    }

    function generateAgentTest() {
        const config = readAgentForm();
        const validationError = validateAgent(config);
        if (validationError) {
            setStatus(elements.agentTestStatus, validationError, 'error');
            return;
        }
        const enabledMcps = state.mcps.filter(mcp => mcp.enabled).map(mcp => ({ key: mcp.key, name: mcp.name, url: mcp.url, transport: mcp.transport }));
        const packageJson = {
            agent: {
                name: config.name,
                provider: config.provider,
                key: config.key,
                runtime: config.runtime,
                allowed_tools_and_scopes: config.tools,
                instructions: config.instructions
            },
            scenario: config.testScenario || 'Describe a test scenario before generating the package.',
            enabled_mcp_services: enabledMcps,
            expected_response_shape: {
                summary: 'Short finding',
                confidence: 'low | medium | high',
                next_actions: ['action one', 'action two'],
                data_or_tool_needs: ['optional follow-up']
            }
        };
        elements.agentTestResult.textContent = JSON.stringify(packageJson, null, 2);
        setStatus(elements.agentTestStatus, 'Agent handoff test package generated.', 'success');
    }

    function extractTools(result) {
        if (!result) return [];
        if (Array.isArray(result.tools)) return result.tools;
        if (result.result && Array.isArray(result.result.tools)) return result.result.tools;
        if (Array.isArray(result)) return result;
        return [];
    }

    function renderToolList(tools) {
        discoveredTools = tools || [];
        elements.toolSelect.innerHTML = '';
        if (!discoveredTools.length) {
            elements.toolsList.textContent = 'Connect to an MCP server to list tools.';
            elements.toolSelect.innerHTML = '<option value="">Load tools to populate options</option>';
            elements.toolCount.textContent = 'No tools loaded';
            return;
        }
        elements.toolCount.textContent = `${discoveredTools.length} tool${discoveredTools.length === 1 ? '' : 's'} loaded`;
        elements.toolsList.innerHTML = '';
        discoveredTools.forEach(tool => {
            const option = document.createElement('option');
            option.value = tool.name || '';
            option.textContent = tool.name || 'Unnamed tool';
            elements.toolSelect.appendChild(option);

            const card = document.createElement('div');
            card.className = 'ai-tool-card';
            const schema = tool.inputSchema || tool.input_schema || {};
            card.innerHTML = `
                <h5>${escapeHtml(tool.name || 'Unnamed tool')}</h5>
                <p>${escapeHtml(tool.description || 'No description provided.')}</p>
                <small>${escapeHtml(JSON.stringify(schema))}</small>
            `;
            elements.toolsList.appendChild(card);
        });
        applySelectedToolExample();
    }

    function applySelectedToolExample() {
        const tool = discoveredTools.find(item => item.name === elements.toolSelect.value);
        const schema = tool && (tool.inputSchema || tool.input_schema);
        const properties = schema && schema.properties ? schema.properties : null;
        if (!properties) return;
        const example = {};
        Object.entries(properties).forEach(([key, value]) => {
            if (value && value.default !== undefined) example[key] = value.default;
            else if (value && value.type === 'number') example[key] = 0;
            else if (value && value.type === 'integer') example[key] = 1;
            else if (value && value.type === 'boolean') example[key] = false;
            else if (value && value.type === 'array') example[key] = [];
            else if (value && value.type === 'object') example[key] = {};
            else example[key] = '';
        });
        elements.toolArguments.value = JSON.stringify(example, null, 2);
    }

    function parseArgumentsJson() {
        const raw = elements.toolArguments.value.trim();
        if (!raw) return {};
        try {
            return JSON.parse(raw);
        } catch (error) {
            throw new Error(`Tool arguments must be valid JSON: ${error.message}`);
        }
    }

    async function sendMcpTest(method, includeTool) {
        const config = readMcpForm();
        const validationError = validateMcp(config);
        if (validationError) {
            setStatus(elements.mcpTestStatus, validationError, 'error');
            return null;
        }
        const payload = {
            url: config.url,
            token: config.token,
            transport: config.transport,
            method
        };
        if (includeTool) {
            payload.tool_name = elements.toolSelect.value;
            if (!payload.tool_name) {
                setStatus(elements.mcpTestStatus, 'Choose a tool before running a test call.', 'error');
                return null;
            }
            try {
                payload.arguments = parseArgumentsJson();
            } catch (error) {
                setStatus(elements.mcpTestStatus, error.message, 'error');
                return null;
            }
        }

        setStatus(elements.mcpTestStatus, `Running ${method} against ${config.name}...`, 'warning');
        elements.testResult.textContent = '';
        try {
            const response = await fetch('/ai/mcp/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json().catch(() => ({}));
            elements.testResult.textContent = JSON.stringify(data, null, 2);
            if (!response.ok) {
                setStatus(elements.mcpTestStatus, data.detail || `MCP test failed with HTTP ${response.status}.`, 'error');
                return null;
            }
            setStatus(elements.mcpTestStatus, `${method} completed for ${config.name}.`, 'success');
            return data;
        } catch (error) {
            console.warn('Unable to test MCP server.', error);
            setStatus(elements.mcpTestStatus, 'Unable to reach the MCP test endpoint from this browser.', 'error');
            return null;
        }
    }

    async function listTools() {
        const method = elements.mcpMethod.value;
        const data = await sendMcpTest(method, false);
        if (data && method === 'tools/list') renderToolList(extractTools(data.result));
    }

    function bindElements() {
        elements.agentSummaryPill = $('agent-summary-pill');
        elements.mcpSummaryPill = $('mcp-summary-pill');
        elements.enabledSummaryPill = $('enabled-summary-pill');
        elements.agentOverviewText = $('agent-overview-text');
        elements.mcpOverviewText = $('mcp-overview-text');
        elements.agentList = $('agent-list');
        elements.mcpList = $('mcp-list');
        elements.addAgent = $('add-agent');
        elements.addMcp = $('add-mcp');
        elements.resetAll = $('ai-reset-all');
        elements.agentForm = $('agent-form');
        elements.agentEnabled = $('agent-enabled');
        elements.agentName = $('agent-name');
        elements.agentProvider = $('agent-provider');
        elements.agentKey = $('agent-key');
        elements.agentRuntime = $('agent-runtime');
        elements.agentTools = $('agent-tools');
        elements.agentInstructions = $('agent-instructions');
        elements.agentNotes = $('agent-notes');
        elements.agentStatus = $('agent-status');
        elements.newAgent = $('new-agent');
        elements.deleteAgent = $('delete-agent');
        elements.selectedAgentPill = $('selected-agent-pill');
        elements.agentTestScenario = $('agent-test-scenario');
        elements.runAgentTest = $('run-agent-test');
        elements.copyAgentTest = $('copy-agent-test');
        elements.agentTestStatus = $('agent-test-status');
        elements.agentTestResult = $('agent-test-result');
        elements.mcpForm = $('mcp-form');
        elements.mcpEnabled = $('mcp-enabled');
        elements.mcpName = $('mcp-name');
        elements.mcpKey = $('mcp-key');
        elements.mcpUrl = $('mcp-url');
        elements.mcpVsCodeType = $('mcp-vscode-type');
        elements.mcpTransport = $('mcp-transport');
        elements.mcpToken = $('mcp-token');
        elements.mcpNotes = $('mcp-notes');
        elements.mcpStatus = $('mcp-status');
        elements.newMcp = $('new-mcp');
        elements.deleteMcp = $('delete-mcp');
        elements.selectedMcpPill = $('selected-mcp-pill');
        elements.mcpToggleToken = $('mcp-toggle-token');
        elements.mcpIncludeToken = $('mcp-include-token');
        elements.vscodeSnippet = $('vscode-snippet');
        elements.pythonSnippet = $('python-snippet');
        elements.copyVsCode = $('copy-vscode');
        elements.copyPython = $('copy-python');
        elements.mcpMethod = $('mcp-method');
        elements.toolSelect = $('tool-select');
        elements.toolArguments = $('tool-arguments');
        elements.listTools = $('list-tools');
        elements.testTool = $('test-tool');
        elements.copyResult = $('copy-result');
        elements.mcpTestStatus = $('mcp-test-status');
        elements.toolsList = $('tools-list');
        elements.testResult = $('test-result');
        elements.toolCount = $('tool-count');
    }

    function bindEvents() {
        elements.agentList.addEventListener('click', selectConfig);
        elements.mcpList.addEventListener('click', selectConfig);
        elements.addAgent.addEventListener('click', addAgent);
        elements.newAgent.addEventListener('click', addAgent);
        elements.addMcp.addEventListener('click', addMcp);
        elements.newMcp.addEventListener('click', addMcp);
        elements.deleteAgent.addEventListener('click', deleteSelectedAgent);
        elements.deleteMcp.addEventListener('click', deleteSelectedMcp);
        elements.resetAll.addEventListener('click', resetAll);
        elements.agentForm.addEventListener('submit', saveAgent);
        elements.mcpForm.addEventListener('submit', saveMcp);
        elements.mcpToggleToken.addEventListener('click', toggleTokenVisibility);
        elements.mcpIncludeToken.addEventListener('change', renderSnippets);
        elements.runAgentTest.addEventListener('click', generateAgentTest);
        elements.copyAgentTest.addEventListener('click', () => copyText(elements.agentTestResult.textContent, 'Agent test package copied.', (message, type) => setStatus(elements.agentTestStatus, message, type)));
        elements.copyVsCode.addEventListener('click', () => copyText(elements.vscodeSnippet.textContent, 'VS Code MCP config copied.', (message, type) => setStatus(elements.mcpStatus, message, type)));
        elements.copyPython.addEventListener('click', () => copyText(elements.pythonSnippet.textContent, 'Python SDK example copied.', (message, type) => setStatus(elements.mcpStatus, message, type)));
        elements.listTools.addEventListener('click', listTools);
        elements.testTool.addEventListener('click', () => sendMcpTest('tools/call', true));
        elements.toolSelect.addEventListener('change', applySelectedToolExample);
        elements.copyResult.addEventListener('click', () => copyText(elements.testResult.textContent, 'MCP test result copied.', (message, type) => setStatus(elements.mcpTestStatus, message, type)));

        [
            elements.mcpName,
            elements.mcpKey,
            elements.mcpUrl,
            elements.mcpVsCodeType,
            elements.mcpTransport,
            elements.mcpToken,
            elements.mcpNotes,
            elements.mcpEnabled
        ].forEach(element => {
            element.addEventListener('input', renderSnippets);
            element.addEventListener('change', renderSnippets);
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        bindElements();
        bindEvents();
        const workspace = loadWorkspace();
        state.agents = workspace.agents;
        state.mcps = workspace.mcps;
        state.selectedAgentId = workspace.selectedAgentId;
        state.selectedMcpId = workspace.selectedMcpId;
        renderAll();
    });
})();
