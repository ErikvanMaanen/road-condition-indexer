(() => {
    const state = {
        services: [],
        urlCheckTypes: [],
        pollingUnits: [],
        monitors: [],
        editingId: null,
        graphChart: null,
    };

    const elements = {
        form: document.getElementById('monitor-form'),
        formHeading: document.getElementById('monitor-form-heading'),
        name: document.getElementById('monitor-name'),
        service: document.getElementById('monitor-service'),
        target: document.getElementById('monitor-target'),
        urlOptions: document.getElementById('monitor-url-options'),
        urlCheck: document.getElementById('monitor-url-check'),
        timeout: document.getElementById('monitor-timeout'),
        intervalValue: document.getElementById('monitor-interval-value'),
        intervalUnit: document.getElementById('monitor-interval-unit'),
        portWrapper: document.getElementById('monitor-port-wrapper'),
        port: document.getElementById('monitor-port'),
        notes: document.getElementById('monitor-notes'),
        enabled: document.getElementById('monitor-enabled'),
        cancelEdit: document.getElementById('monitor-cancel-edit'),
        refresh: document.getElementById('monitor-refresh'),
        status: document.getElementById('monitor-form-status'),
        list: document.getElementById('monitor-list'),
        empty: document.getElementById('monitor-empty'),
        overlay: document.getElementById('monitor-log-overlay'),
        overlayClose: document.getElementById('monitor-log-close'),
        overlayContent: document.getElementById('monitor-log-content'),
        overlayTitle: document.getElementById('monitor-log-title'),
        graphOverlay: document.getElementById('monitor-graph-overlay'),
        graphClose: document.getElementById('monitor-graph-close'),
        graphCanvas: document.getElementById('monitor-graph-canvas'),
        graphEmpty: document.getElementById('monitor-graph-empty'),
        graphTitle: document.getElementById('monitor-graph-title'),
    };

    const PORT_SERVICE_TYPES = new Set(['tcp', 'udp', 'smtp', 'imap', 'pop3', 'ftp', 'sftp', 'ssh', 'dns']);
    const URL_SERVICE_TYPES = new Set(['http', 'https', 'url']);
    const ACTIVE_RUN_TYPES = new Set([
        ...URL_SERVICE_TYPES,
        'ping',
        'tcp',
        'smtp',
        'imap',
        'pop3',
        'ftp',
        'sftp',
        'ssh',
        'dns',
    ]);

    const DEFAULT_PORT_PLACEHOLDERS = {
        smtp: '25',
        imap: '143',
        pop3: '110',
        ftp: '21',
        sftp: '22',
        ssh: '22',
        dns: '53',
    };

    function escapeHtml(value) {
        if (value == null) {
            return '';
        }
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function formatDate(value) {
        if (!value) {
            return '—';
        }
        try {
            return typeof formatDutchTime === 'function' ? formatDutchTime(value) : new Date(value).toLocaleString();
        } catch (error) {
            return value;
        }
    }

    function setFormStatus(message, type = 'info') {
        if (!elements.status) return;
        elements.status.textContent = message || '';
        if (!message) {
            elements.status.classList.remove('status-success', 'status-error');
            elements.status.style.display = 'none';
            return;
        }
        elements.status.style.display = 'block';
        elements.status.classList.remove('status-success', 'status-error');
        if (type === 'success') {
            elements.status.classList.add('status-success');
        } else if (type === 'error') {
            elements.status.classList.add('status-error');
        }
    }

    function toggleElement(element, show) {
        if (!element) return;
        element.classList.toggle('hidden', !show);
        element.setAttribute('aria-hidden', show ? 'false' : 'true');
        if (!show) {
            element.querySelectorAll('input, select, textarea').forEach((input) => {
                input.value = '';
            });
        }
    }

    function toggleUrlOptions(serviceType) {
        const shouldShow = URL_SERVICE_TYPES.has(serviceType);
        toggleElement(elements.urlOptions, shouldShow);
        if (elements.urlCheck) {
            elements.urlCheck.value = 'availability';
        }
        if (!shouldShow && elements.timeout) {
            elements.timeout.value = '';
        }
    }

    function togglePortField(serviceType) {
        const shouldShow = PORT_SERVICE_TYPES.has(serviceType);
        if (!elements.portWrapper) return;
        elements.portWrapper.classList.toggle('hidden', !shouldShow);
        elements.portWrapper.setAttribute('aria-hidden', shouldShow ? 'false' : 'true');
        if (shouldShow) {
            const placeholder = DEFAULT_PORT_PLACEHOLDERS[serviceType] || 'Bijvoorbeeld 443';
            elements.port.placeholder = placeholder;
        } else {
            elements.port.value = '';
        }
    }

    function resetForm() {
        state.editingId = null;
        elements.formHeading.textContent = 'Nieuwe monitor toevoegen';
        elements.form.reset();
        elements.intervalValue.value = '5';
        if (elements.intervalUnit) {
            elements.intervalUnit.value = 'minutes';
        }
        if (elements.enabled) {
            elements.enabled.checked = true;
        }
        toggleUrlOptions(elements.service.value || 'http');
        togglePortField(elements.service.value || 'http');
        elements.cancelEdit.classList.add('hidden');
        setFormStatus('');
        elements.name.focus();
    }

    function getIntervalParts(seconds) {
        const mappings = [
            { unit: 'days', label: 'days', seconds: 86400 },
            { unit: 'hours', label: 'hours', seconds: 3600 },
            { unit: 'minutes', label: 'minutes', seconds: 60 },
            { unit: 'seconds', label: 'seconds', seconds: 1 },
        ];

        for (const mapping of mappings) {
            if (seconds % mapping.seconds === 0) {
                return { value: String(seconds / mapping.seconds), unit: mapping.unit };
            }
        }
        return { value: String(seconds), unit: 'seconds' };
    }

    async function loadMetadata() {
        try {
            const response = await fetch('/api/monitors/metadata');
            if (!response.ok) {
                throw new Error('Kon metadata niet laden');
            }
            const payload = await response.json();
            state.services = Array.isArray(payload.services) ? payload.services : [];
            state.urlCheckTypes = Array.isArray(payload.url_check_types) ? payload.url_check_types : [];
            state.pollingUnits = Array.isArray(payload.polling_units) ? payload.polling_units : ['seconds', 'minutes', 'hours', 'days'];

            if (elements.service) {
                elements.service.innerHTML = state.services
                    .map((entry) => `<option value="${escapeHtml(entry.id)}">${escapeHtml(entry.label)}</option>`)
                    .join('');
            }

            if (elements.urlCheck && state.urlCheckTypes.length) {
                elements.urlCheck.innerHTML = state.urlCheckTypes
                    .map((entry) => `<option value="${escapeHtml(entry)}">${escapeHtml(entry.charAt(0).toUpperCase() + entry.slice(1))}</option>`)
                    .join('');
            }

            if (elements.intervalUnit && state.pollingUnits.length) {
                elements.intervalUnit.innerHTML = state.pollingUnits
                    .map((entry) => {
                        const label = entry.charAt(0).toUpperCase() + entry.slice(1);
                        return `<option value="${escapeHtml(entry)}">${escapeHtml(label)}</option>`;
                    })
                    .join('');
                elements.intervalUnit.value = state.pollingUnits.includes('minutes') ? 'minutes' : state.pollingUnits[0];
            }

            toggleUrlOptions(elements.service.value || 'http');
            togglePortField(elements.service.value || 'http');
        } catch (error) {
            console.error(error);
            setFormStatus('Kon metadata niet laden.', 'error');
        }
    }

    async function loadMonitors(showToast = false) {
        elements.list.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch('/api/monitors?include_history=true&history_limit=40');
            if (!response.ok) {
                throw new Error('Kon monitors niet ophalen');
            }
            const payload = await response.json();
            state.monitors = Array.isArray(payload.monitors) ? payload.monitors : [];
            renderMonitors();
            if (showToast) {
                setFormStatus('Monitoroverzicht vernieuwd.', 'success');
            }
        } catch (error) {
            console.error(error);
            setFormStatus('Kon monitors niet ophalen.', 'error');
        } finally {
            elements.list.setAttribute('aria-busy', 'false');
        }
    }

    function summarizeResults(results) {
        const summary = { success: 0, warning: 0, failure: 0, change: 0 };
        (results || []).forEach((result) => {
            const status = (result.status || '').toLowerCase();
            if (status === 'warning') {
                summary.warning += 1;
            } else if (status === 'success') {
                summary.success += 1;
            } else if (status === 'failure') {
                summary.failure += 1;
            } else {
                summary.failure += 1;
            }
            if (result.change_detected) {
                summary.change += 1;
            }
        });
        return summary;
    }

    function renderChangeSummary(details) {
        if (!details || typeof details.change_summary !== 'string' || !details.change_summary.trim()) {
            return '';
        }
        const referenceTime = details.change_reference_checked_at ? formatDate(details.change_reference_checked_at) : null;
        const parts = [
            '<div class="monitor-log-change">',
            '<div class="monitor-log-change-heading">Wijziging t.o.v. stabiele versie</div>',
            `<pre class="monitor-log-diff">${escapeHtml(details.change_summary)}</pre>`,
        ];
        if (referenceTime) {
            parts.push(`<div class="monitor-log-change-meta">Referentie: ${escapeHtml(referenceTime)}</div>`);
        }
        parts.push('</div>');
        return parts.join('');
    }

    function getStatusMeta(monitor) {
        const latest = (monitor.recent_results || [])[0] || null;
        const statusValue = (latest && latest.status) || monitor.last_status || 'unknown';
        const normalized = statusValue.toLowerCase();
        let label = 'Onbekend';
        let css = 'monitor-status-neutral';
        if (normalized === 'success') {
            label = 'Online';
            css = 'monitor-status-success';
        } else if (normalized === 'warning') {
            label = 'Wijziging';
            css = 'monitor-status-warning';
        } else if (normalized === 'failure') {
            label = 'Storing';
            css = 'monitor-status-failure';
        }
        return { label, css, latest };
    }

    function renderMonitors() {
        elements.list.innerHTML = '';
        if (!state.monitors.length) {
            elements.empty.classList.remove('hidden');
            return;
        }
        elements.empty.classList.add('hidden');

        state.monitors.forEach((monitor) => {
            const card = document.createElement('article');
            card.className = 'monitor-item';
            const { label: statusLabel, css: statusClass, latest } = getStatusMeta(monitor);
            const lastChecked = latest?.checked_at || monitor.last_checked_at;
            const lastMessage = latest?.message || monitor.last_message || '—';
            const responseTime = typeof latest?.response_time_ms === 'number' ? `${latest.response_time_ms} ms` : '—';
            const availability = latest?.is_available == null ? '—' : latest.is_available ? 'Ja' : 'Nee';
            const changeCount = summarizeResults(monitor.recent_results || []).change;
            const enabled = monitor.is_enabled !== false;

            card.innerHTML = `
                <header class="monitor-item-head">
                    <div class="monitor-item-meta">
                        <h3 class="monitor-item-title">${escapeHtml(monitor.name)}</h3>
                        <span class="monitor-item-type">${escapeHtml(monitor.service_label || monitor.service_type)}</span>
                    </div>
                    <div class="monitor-item-controls">
                        <button type="button" class="monitor-toggle focus-ring ${enabled ? '' : 'is-off'}" data-action="toggle" aria-pressed="${enabled ? 'true' : 'false'}">${enabled ? 'Aan' : 'Uit'}</button>
                        <span class="monitor-status ${statusClass}">${escapeHtml(statusLabel)}</span>
                    </div>
                </header>
                <dl class="monitor-item-grid">
                    <div>
                        <dt>Doel</dt>
                        <dd title="${escapeHtml(monitor.target)}">${escapeHtml(monitor.target)}</dd>
                    </div>
                    <div>
                        <dt>Interval</dt>
                        <dd>${escapeHtml(monitor.polling_interval?.display || '')}</dd>
                    </div>
                    <div>
                        <dt>Laatst</dt>
                        <dd>${escapeHtml(formatDate(lastChecked))}</dd>
                    </div>
                    <div>
                        <dt>Beschikbaar</dt>
                        <dd>${escapeHtml(availability)}</dd>
                    </div>
                    <div>
                        <dt>Ping</dt>
                        <dd>${escapeHtml(responseTime)}</dd>
                    </div>
                    <div>
                        <dt>Wijziging</dt>
                        <dd>${changeCount}</dd>
                    </div>
                </dl>
                <p class="monitor-item-message">${escapeHtml(lastMessage)}</p>
                ${monitor.notes ? `<p class="monitor-item-notes">${escapeHtml(monitor.notes)}</p>` : ''}
                <div class="monitor-item-actions">
                    <button type="button" class="focus-ring" data-action="run" ${ACTIVE_RUN_TYPES.has(monitor.service_type) ? '' : 'disabled'}>Check</button>
                    <button type="button" class="secondary-button focus-ring" data-action="graph">Grafiek</button>
                    <button type="button" class="secondary-button focus-ring" data-action="log">Log</button>
                    <button type="button" class="secondary-button focus-ring" data-action="edit">Bewerk</button>
                    <button type="button" class="danger-button focus-ring" data-action="delete">Verwijder</button>
                </div>
            `;

            const toggleButton = card.querySelector('[data-action="toggle"]');
            toggleButton.addEventListener('click', () => toggleMonitor(monitor, !enabled));
            card.querySelector('[data-action="edit"]').addEventListener('click', () => beginEditMonitor(monitor));
            card.querySelector('[data-action="delete"]').addEventListener('click', () => deleteMonitor(monitor));
            card.querySelector('[data-action="log"]').addEventListener('click', () => openLogOverlay(monitor));
            card.querySelector('[data-action="graph"]').addEventListener('click', () => openGraphOverlay(monitor));
            const runButton = card.querySelector('[data-action="run"]');
            if (runButton && !runButton.disabled) {
                runButton.addEventListener('click', () => runMonitor(monitor));
            }

            elements.list.appendChild(card);
        });
    }

    function populateForm(monitor) {
        state.editingId = monitor.id;
        elements.formHeading.textContent = 'Monitor bijwerken';
        elements.name.value = monitor.name || '';
        elements.service.value = monitor.service_type;
        elements.target.value = monitor.target || '';
        const intervalParts = getIntervalParts(Number(monitor.polling_interval?.seconds || monitor.polling_interval_seconds || 60));
        elements.intervalValue.value = intervalParts.value;
        elements.intervalUnit.value = intervalParts.unit;
        toggleUrlOptions(monitor.service_type);
        togglePortField(monitor.service_type);
        if (ACTIVE_RUN_TYPES.has(monitor.service_type)) {
            elements.urlCheck.value = monitor.url_check_type || 'availability';
            elements.timeout.value = monitor.config?.timeout || '';
        }
        if (PORT_SERVICE_TYPES.has(monitor.service_type) && monitor.config?.port) {
            elements.port.value = monitor.config.port;
        }
        elements.notes.value = monitor.notes || '';
        if (elements.enabled) {
            elements.enabled.checked = monitor.is_enabled !== false;
        }
        elements.cancelEdit.classList.remove('hidden');
        setFormStatus('');
    }

    async function submitForm(event) {
        event.preventDefault();
        setFormStatus('');

        if (!elements.form.checkValidity()) {
            setFormStatus('Controleer de invoer en probeer opnieuw.', 'error');
            return;
        }

        const payload = {
            name: elements.name.value.trim(),
            service_type: elements.service.value,
            target: elements.target.value.trim(),
            polling_value: Number(elements.intervalValue.value || 0),
            polling_unit: elements.intervalUnit.value,
            url_check_type: ACTIVE_RUN_TYPES.has(elements.service.value) ? elements.urlCheck.value : null,
            notes: elements.notes.value.trim() || null,
            is_enabled: elements.enabled ? Boolean(elements.enabled.checked) : true,
            config: {},
        };

        if (elements.timeout && elements.timeout.value) {
            const timeoutValue = Number(elements.timeout.value);
            if (!Number.isNaN(timeoutValue)) {
                payload.config.timeout = timeoutValue;
            }
        }

        if (PORT_SERVICE_TYPES.has(elements.service.value)) {
            const portValue = Number(elements.port.value);
            if (!Number.isNaN(portValue) && portValue > 0) {
                payload.config.port = portValue;
            }
        }

        if (!Object.keys(payload.config).length) {
            delete payload.config;
        }

        const isUpdate = state.editingId != null;
        const endpoint = isUpdate ? `/api/monitors/${state.editingId}` : '/api/monitors';
        const method = isUpdate ? 'PUT' : 'POST';

        try {
            const response = await fetch(endpoint, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!response.ok) {
                const errorPayload = await response.json().catch(() => ({}));
                throw new Error(errorPayload.detail || 'Opslaan mislukt');
            }
            await loadMonitors();
            setFormStatus(isUpdate ? 'Monitor bijgewerkt.' : 'Monitor toegevoegd.', 'success');
            resetForm();
        } catch (error) {
            console.error(error);
            setFormStatus(error.message || 'Opslaan mislukt.', 'error');
        }
    }

    function beginEditMonitor(monitor) {
        populateForm(monitor);
        elements.name.focus();
    }

    async function deleteMonitor(monitor) {
        if (!window.confirm(`Weet je zeker dat je '${monitor.name}' wilt verwijderen?`)) {
            return;
        }
        try {
            const response = await fetch(`/api/monitors/${monitor.id}`, { method: 'DELETE' });
            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                throw new Error(payload.detail || 'Verwijderen mislukt');
            }
            await loadMonitors();
            setFormStatus('Monitor verwijderd.', 'success');
            if (state.editingId === monitor.id) {
                resetForm();
            }
        } catch (error) {
            console.error(error);
            setFormStatus(error.message || 'Verwijderen mislukt.', 'error');
        }
    }

    async function runMonitor(monitor) {
        try {
            const response = await fetch(`/api/monitors/${monitor.id}/run`, { method: 'POST' });
            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                throw new Error(payload.detail || 'Controle uitvoeren mislukt');
            }
            await loadMonitors(true);
        } catch (error) {
            console.error(error);
            setFormStatus(error.message || 'Controle uitvoeren mislukt.', 'error');
        }
    }

    function destroyGraphChart() {
        if (state.graphChart && typeof state.graphChart.destroy === 'function') {
            state.graphChart.destroy();
        }
        state.graphChart = null;
    }

    async function toggleMonitor(monitor, desiredState) {
        try {
            const response = await fetch(`/api/monitors/${monitor.id}/toggle`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_enabled: desiredState }),
            });
            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                throw new Error(payload.detail || 'Status bijwerken mislukt');
            }
            const payload = await response.json();
            const updated = payload.monitor || {};
            if (!Array.isArray(updated.recent_results)) {
                updated.recent_results = monitor.recent_results || [];
            }
            const index = state.monitors.findIndex((entry) => entry.id === monitor.id);
            if (index !== -1) {
                state.monitors[index] = updated;
            }
            if (state.editingId === monitor.id) {
                populateForm(updated);
            }
            renderMonitors();
            setFormStatus(desiredState ? 'Monitor geactiveerd.' : 'Monitor gepauzeerd.', 'success');
        } catch (error) {
            console.error(error);
            setFormStatus(error.message || 'Status bijwerken mislukt.', 'error');
        }
    }

    async function openGraphOverlay(monitor) {
        if (!elements.graphOverlay) {
            return;
        }

        destroyGraphChart();
        if (elements.graphTitle) {
            elements.graphTitle.textContent = `Grafiek · ${monitor.name}`;
        }
        if (elements.graphEmpty) {
            elements.graphEmpty.textContent = 'Grafiek wordt geladen...';
            elements.graphEmpty.classList.remove('hidden');
        }
        if (elements.graphCanvas) {
            elements.graphCanvas.classList.add('hidden');
        }

        elements.graphOverlay.classList.remove('hidden');
        if (elements.graphClose) {
            elements.graphClose.focus();
        }

        let results = [];
        try {
            const response = await fetch(`/api/monitors/${monitor.id}/history`);
            if (!response.ok) {
                throw new Error('Kon monitorhistorie niet ophalen');
            }
            const payload = await response.json();
            results = Array.isArray(payload.results) ? payload.results : [];
        } catch (error) {
            console.error(error);
            if (elements.graphEmpty) {
                elements.graphEmpty.textContent = 'Kon gegevens niet laden.';
            }
            return;
        }

        if (!results.length || !elements.graphCanvas) {
            if (elements.graphCanvas) {
                elements.graphCanvas.classList.add('hidden');
            }
            if (elements.graphEmpty) {
                elements.graphEmpty.textContent = 'Geen meetpunten beschikbaar.';
                elements.graphEmpty.classList.remove('hidden');
            }
            return;
        }

        if (elements.graphCanvas) {
            elements.graphCanvas.classList.remove('hidden');
        }
        if (elements.graphEmpty) {
            elements.graphEmpty.classList.add('hidden');
        }

        const labels = results.map((entry) => formatDate(entry.checked_at));
        const values = results.map((entry) => (typeof entry.response_time_ms === 'number' ? entry.response_time_ms : null));
        const datasetLabel = monitor.service_type === 'ping' ? 'Ping (ms)' : 'Responstijd (ms)';
        const colors = results.map((entry) => {
            const status = (entry.status || '').toLowerCase();
            if (status === 'success') {
                return 'rgba(25,135,84,0.9)';
            }
            if (status === 'warning') {
                return 'rgba(255,193,7,0.9)';
            }
            if (status === 'failure') {
                return 'rgba(220,53,69,0.9)';
            }
            return 'rgba(108,117,125,0.9)';
        });

        const context = elements.graphCanvas.getContext('2d');
        state.graphChart = new Chart(context, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: datasetLabel,
                        data: values,
                        borderColor: 'rgba(73,80,87,0.75)',
                        backgroundColor: 'rgba(73,80,87,0.12)',
                        pointBackgroundColor: colors,
                        pointBorderColor: colors,
                        spanGaps: true,
                        tension: 0.2,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label(context) {
                                const value = context.parsed.y;
                                const responseText = value == null ? 'n.v.t.' : `${value} ms`;
                                const result = results[context.dataIndex];
                                const status = (result?.status || '').toUpperCase();
                                return `${responseText}${status ? ` · ${status}` : ''}`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { maxRotation: 0 },
                    },
                    y: {
                        grid: { color: 'rgba(0,0,0,0.08)' },
                        ticks: { precision: 0 },
                    },
                },
                elements: {
                    point: { radius: 3 },
                },
            },
        });
    }

    function closeGraphOverlay() {
        if (!elements.graphOverlay) {
            return;
        }
        destroyGraphChart();
        elements.graphOverlay.classList.add('hidden');
        if (elements.graphEmpty) {
            elements.graphEmpty.classList.add('hidden');
        }
    }

    async function openLogOverlay(monitor) {
        elements.overlay.classList.remove('hidden');
        elements.overlayTitle.textContent = `Monitorlog · ${monitor.name}`;
        elements.overlayContent.innerHTML = '<p class="rci-muted">Log wordt geladen...</p>';

        try {
            const response = await fetch(`/api/monitors/${monitor.id}/logs?limit=200`);
            if (!response.ok) {
                throw new Error('Kon monitorlog niet ophalen');
            }
            const payload = await response.json();
            const results = payload.results || [];
            if (!results.length) {
                elements.overlayContent.innerHTML = '<p class="rci-muted">Nog geen loggegevens beschikbaar.</p>';
                return;
            }

            const rows = results
                .map((result) => {
                    const status = escapeHtml((result.status || '').toUpperCase());
                    const available = result.is_available == null ? '—' : result.is_available ? 'Ja' : 'Nee';
                    const responseTime = typeof result.response_time_ms === 'number' ? `${result.response_time_ms} ms` : '—';
                    const changeSummaryHtml = renderChangeSummary(result.details || {});
                    return `
                        <tr>
                            <td>${escapeHtml(formatDate(result.checked_at))}</td>
                            <td>${status}</td>
                            <td>${escapeHtml(available)}</td>
                            <td>${escapeHtml(responseTime)}</td>
                            <td>
                                ${escapeHtml(result.message || '')}
                                ${changeSummaryHtml}
                            </td>
                        </tr>
                    `;
                })
                .join('');

            elements.overlayContent.innerHTML = `
                <table class="monitor-log-table">
                    <thead>
                        <tr>
                            <th>Tijdstip</th>
                            <th>Status</th>
                            <th>Beschikbaar</th>
                            <th>Respons</th>
                            <th>Bericht</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            `;
        } catch (error) {
            console.error(error);
            elements.overlayContent.innerHTML = '<p class="status-error">Kon monitorlog niet laden.</p>';
        }

        elements.overlayClose.focus();
    }

    function closeOverlay() {
        elements.overlay.classList.add('hidden');
        elements.overlayContent.innerHTML = '';
    }

    function handleServiceChange() {
        const serviceType = elements.service.value;
        toggleUrlOptions(serviceType);
        togglePortField(serviceType);
    }

    function initialize() {
        if (!elements.form) {
            return;
        }
        elements.form.addEventListener('submit', submitForm);
        elements.cancelEdit.addEventListener('click', resetForm);
        elements.refresh.addEventListener('click', () => loadMonitors(true));
        elements.service.addEventListener('change', handleServiceChange);

        if (elements.overlayClose) {
            elements.overlayClose.addEventListener('click', closeOverlay);
        }
        if (elements.overlay) {
            elements.overlay.addEventListener('click', (event) => {
                if (event.target === elements.overlay) {
                    closeOverlay();
                }
            });
        }
        if (elements.graphClose) {
            elements.graphClose.addEventListener('click', closeGraphOverlay);
        }
        if (elements.graphOverlay) {
            elements.graphOverlay.addEventListener('click', (event) => {
                if (event.target === elements.graphOverlay) {
                    closeGraphOverlay();
                }
            });
        }
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                let handled = false;
                if (elements.overlay && !elements.overlay.classList.contains('hidden')) {
                    closeOverlay();
                    handled = true;
                }
                if (elements.graphOverlay && !elements.graphOverlay.classList.contains('hidden')) {
                    closeGraphOverlay();
                    handled = true;
                }
                if (handled) {
                    event.stopPropagation();
                }
            }
        });

        loadMetadata().then(() => loadMonitors());
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
})();
