(() => {
    const dropZone = document.getElementById('noise-drop-zone');
    const fileInput = document.getElementById('noise-file-input');
    const detailsEl = document.getElementById('noise-file-details');
    const settingsWrapper = document.getElementById('noise-settings-wrapper');
    const processBtn = document.getElementById('noise-process-btn');
    const resetBtn = document.getElementById('noise-reset-btn');
    const logEl = document.getElementById('noise-log');
    const downloadWrap = document.getElementById('noise-download');
    const downloadLink = document.getElementById('noise-download-link');

    const PROFILE_PRESETS = {
        gentle: { noiseReduction: 6, residualFloor: -45, temporalSmoothing: 14, frequencySmoothing: 6 },
        balanced: { noiseReduction: 12, residualFloor: -50, temporalSmoothing: 18, frequencySmoothing: 8 },
        aggressive: { noiseReduction: 20, residualFloor: -56, temporalSmoothing: 26, frequencySmoothing: 11 }
    };

    const FORMAT_LIBRARY = {
        mp3: {
            kind: 'audio',
            label: 'MP3 audio',
            backendKey: 'mp3',
            outputFormats: [
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Best for editing or archiving.' },
                { value: 'flac', label: 'FLAC (lossless)', help: 'Keeps file smaller while lossless.' },
                { value: 'm4a', label: 'M4A (AAC)', help: 'Good balance for sharing.' }
            ]
        },
        wav: {
            kind: 'audio',
            label: 'WAV audio',
            backendKey: 'wav',
            outputFormats: [
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Preserves full quality.' },
                { value: 'flac', label: 'FLAC (lossless)', help: 'Compress without losing quality.' },
                { value: 'm4a', label: 'M4A (AAC)', help: 'Smaller file for distribution.' }
            ]
        },
        flac: {
            kind: 'audio',
            label: 'FLAC audio',
            backendKey: 'flac',
            outputFormats: [
                { value: 'flac', label: 'FLAC (lossless)', help: 'Keep as lossless FLAC.' },
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Great for further processing.' },
                { value: 'm4a', label: 'M4A (AAC)', help: 'Encode to AAC for compatibility.' }
            ]
        },
        ogg: {
            kind: 'audio',
            label: 'Ogg/Vorbis audio',
            backendKey: 'ogg',
            outputFormats: [
                { value: 'flac', label: 'FLAC (lossless)', help: 'Ideal for mastering.' },
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Full quality wave file.' },
                { value: 'm4a', label: 'M4A (AAC)', help: 'Convert for players that do not support OGG.' }
            ]
        },
        m4a: {
            kind: 'audio',
            label: 'M4A audio',
            backendKey: 'm4a',
            outputFormats: [
                { value: 'm4a', label: 'M4A (AAC)', help: 'Keep the MPEG-4 container.' },
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Export an uncompressed master.' },
                { value: 'flac', label: 'FLAC (lossless)', help: 'Store as lossless FLAC.' }
            ]
        },
        aac: {
            kind: 'audio',
            label: 'AAC audio',
            backendKey: 'aac',
            outputFormats: [
                { value: 'm4a', label: 'M4A (AAC)', help: 'Keep AAC audio in M4A container.' },
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Export lossless PCM.' },
                { value: 'flac', label: 'FLAC (lossless)', help: 'Archive as lossless FLAC.' }
            ]
        },
        wma: {
            kind: 'audio',
            label: 'WMA audio',
            backendKey: 'wma',
            outputFormats: [
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Re-encode to wave for editing.' },
                { value: 'flac', label: 'FLAC (lossless)', help: 'Lossless archival copy.' },
                { value: 'm4a', label: 'M4A (AAC)', help: 'Convert to AAC for compatibility.' }
            ]
        },
        mp4: {
            kind: 'video',
            label: 'MP4 video',
            backendKey: 'mp4',
            outputFormats: [
                { value: 'mp4', label: 'MP4 (H.264 + AAC)', help: 'Universal compatibility.' },
                { value: 'mkv', label: 'MKV (H.264 + AAC)', help: 'Matroska container with AAC audio.' }
            ]
        },
        mov: {
            kind: 'video',
            label: 'QuickTime/MOV video',
            backendKey: 'mov',
            outputFormats: [
                { value: 'mov', label: 'MOV (H.264 + AAC)', help: 'QuickTime compatible output.' },
                { value: 'mp4', label: 'MP4 (H.264 + AAC)', help: 'Widely supported mp4 container.' },
                { value: 'mkv', label: 'MKV (H.264 + AAC)', help: 'Matroska container.' }
            ]
        },
        mkv: {
            kind: 'video',
            label: 'Matroska video',
            backendKey: 'mkv',
            outputFormats: [
                { value: 'mkv', label: 'MKV (H.264 + AAC)', help: 'Matroska container output.' },
                { value: 'mp4', label: 'MP4 (H.264 + AAC)', help: 'Export as MP4 for portability.' }
            ]
        },
        avi: {
            kind: 'video',
            label: 'AVI video',
            backendKey: 'avi',
            outputFormats: [
                { value: 'mp4', label: 'MP4 (H.264 + AAC)', help: 'Transcode to MP4 for modern playback.' },
                { value: 'mkv', label: 'MKV (H.264 + AAC)', help: 'Store in Matroska container.' }
            ]
        },
        webm: {
            kind: 'video',
            label: 'WebM video',
            backendKey: 'webm',
            outputFormats: [
                { value: 'mkv', label: 'MKV (H.264 + AAC)', help: 'Rewrap with H.264 + AAC output.' },
                { value: 'mp4', label: 'MP4 (H.264 + AAC)', help: 'Convert for wider device support.' }
            ]
        },
        'generic-audio': {
            kind: 'audio',
            label: 'Audio stream',
            backendKey: 'generic-audio',
            outputFormats: [
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Safe uncompressed audio output.' },
                { value: 'flac', label: 'FLAC (lossless)', help: 'Lossless but smaller than WAV.' },
                { value: 'm4a', label: 'M4A (AAC)', help: 'Compressed output for sharing.' }
            ]
        },
        'generic-video': {
            kind: 'video',
            label: 'Video stream',
            backendKey: 'generic-video',
            outputFormats: [
                { value: 'mp4', label: 'MP4 (H.264 + AAC)', help: 'Standard MP4 output.' },
                { value: 'mkv', label: 'MKV (H.264 + AAC)', help: 'Matroska container output.' }
            ]
        }
    };

    let currentFile = null;
    let currentFormat = null;
    let currentSettingsScope = null;

    window.toggleSection = function toggleSection(sectionId) {
        const content = document.getElementById(`${sectionId}-content`);
        const toggle = document.getElementById(`${sectionId}-toggle`);
        if (!content || !toggle) return;
        const shouldOpen = content.style.display === 'none' || content.style.display === '';
        content.style.display = shouldOpen ? 'block' : 'none';
        toggle.textContent = shouldOpen ? '▼' : '▶';
    };

    function resetState() {
        currentFile = null;
        currentFormat = null;
        currentSettingsScope = null;
        settingsWrapper.innerHTML = '';
        detailsEl.textContent = 'No file selected.';
        processBtn.disabled = true;
        resetBtn.disabled = true;
        hideDownload();
        clearLog();
        fileInput.value = '';
    }

    function clearLog() {
        logEl.textContent = '';
    }

    function appendLog(line) {
        logEl.textContent += line + '\n';
        logEl.scrollTop = logEl.scrollHeight;
    }

    function hideDownload() {
        downloadWrap.classList.add('hidden');
        downloadLink.removeAttribute('href');
    }

    function describeFile(file, formatInfo) {
        const sizeKb = (file.size / 1024).toFixed(1);
        const ext = formatInfo && formatInfo.label ? formatInfo.label : 'Unknown format';
        const type = file.type || 'application/octet-stream';
        detailsEl.textContent = `${file.name} — ${ext} (${type}, ${sizeKb} KB)`;
    }

    function selectFormatInfo(file) {
        const ext = (file.name.split('.').pop() || '').toLowerCase();
        let info = FORMAT_LIBRARY[ext];
        if (!info) {
            if (file.type.startsWith('audio/')) {
                info = FORMAT_LIBRARY['generic-audio'];
            } else if (file.type.startsWith('video/')) {
                info = FORMAT_LIBRARY['generic-video'];
            }
        }
        if (!info) {
            return null;
        }
        return {
            ...info,
            extension: ext || (info.kind === 'audio' ? 'generic-audio' : 'generic-video')
        };
    }

    function renderSettings(formatInfo) {
        settingsWrapper.innerHTML = '';
        const templateId = formatInfo.kind === 'video' ? 'noise-video-template' : 'noise-audio-template';
        const tpl = document.getElementById(templateId);
        if (!tpl) {
            return;
        }
        const fragment = tpl.content.cloneNode(true);
        settingsWrapper.appendChild(fragment);
        currentSettingsScope = settingsWrapper;
        configureOptions(formatInfo);
    }

    function configureOptions(formatInfo) {
        const scope = currentSettingsScope;
        if (!scope) return;
        const profileSelect = scope.querySelector('[data-role="profile-select"]');
        const noiseRange = scope.querySelector('[data-role="noise-reduction"]');
        const noiseOut = scope.querySelector('[data-role="noise-reduction-display"]');
        const floorRange = scope.querySelector('[data-role="residual-floor"]');
        const floorOut = scope.querySelector('[data-role="residual-floor-display"]');
        const temporalRange = scope.querySelector('[data-role="temporal-smoothing"]');
        const temporalOut = scope.querySelector('[data-role="temporal-smoothing-display"]');
        const freqRange = scope.querySelector('[data-role="frequency-smoothing"]');
        const freqOut = scope.querySelector('[data-role="frequency-smoothing-display"]');
        const highpassToggle = scope.querySelector('[data-role="highpass-toggle"]');
        const highpassValue = scope.querySelector('[data-role="highpass-value"]');
        const lowpassToggle = scope.querySelector('[data-role="lowpass-toggle"]');
        const lowpassValue = scope.querySelector('[data-role="lowpass-value"]');
        const outputSelect = scope.querySelector('[data-role="output-format"]');
        const outputHelp = scope.querySelector('[data-role="output-help"]');
        const preserveVideo = scope.querySelector('[data-role="preserve-video"]');
        const videoDenoiseToggle = scope.querySelector('[data-role="video-denoise"]');
        const videoDenoiseWrap = scope.querySelector('[data-role="video-denoise-controls"]');
        const videoDenoiseStrength = scope.querySelector('[data-role="video-denoise-strength"]');
        const videoDenoiseStrengthDisplay = scope.querySelector('[data-role="video-denoise-strength-display"]');

        const updateNoiseDisplay = () => {
            if (noiseOut) noiseOut.textContent = `${noiseRange.value} dB`;
        };
        const updateFloorDisplay = () => {
            if (floorOut) floorOut.textContent = `${floorRange.value} dB`;
        };
        const updateTemporalDisplay = () => {
            if (temporalOut) {
                const value = (Number(temporalRange.value) / 10).toFixed(1);
                temporalOut.textContent = `${value}×`;
            }
        };
        const updateFreqDisplay = () => {
            if (freqOut) freqOut.textContent = `${freqRange.value} bands`;
        };
        const updateVideoDenoiseDisplay = () => {
            if (videoDenoiseStrengthDisplay && videoDenoiseStrength) {
                videoDenoiseStrengthDisplay.textContent = `${Number(videoDenoiseStrength.value).toFixed(1)}`;
            }
        };

        updateNoiseDisplay();
        updateFloorDisplay();
        updateTemporalDisplay();
        updateFreqDisplay();
        updateVideoDenoiseDisplay();

        if (profileSelect) {
            profileSelect.addEventListener('change', () => {
                const preset = PROFILE_PRESETS[profileSelect.value];
                if (!preset) {
                    return;
                }
                if (noiseRange) {
                    noiseRange.value = preset.noiseReduction;
                    updateNoiseDisplay();
                }
                if (floorRange) {
                    floorRange.value = preset.residualFloor;
                    updateFloorDisplay();
                }
                if (temporalRange) {
                    temporalRange.value = preset.temporalSmoothing;
                    updateTemporalDisplay();
                }
                if (freqRange) {
                    freqRange.value = preset.frequencySmoothing;
                    updateFreqDisplay();
                }
            });
        }

        const markCustomProfile = () => {
            if (profileSelect && profileSelect.value !== 'custom') {
                profileSelect.value = 'custom';
            }
        };

        [noiseRange, floorRange, temporalRange, freqRange].forEach(control => {
            if (!control) return;
            control.addEventListener('input', () => {
                if (control === noiseRange) updateNoiseDisplay();
                if (control === floorRange) updateFloorDisplay();
                if (control === temporalRange) updateTemporalDisplay();
                if (control === freqRange) updateFreqDisplay();
                markCustomProfile();
            });
        });

        if (highpassToggle && highpassValue) {
            highpassToggle.addEventListener('change', () => {
                highpassValue.disabled = !highpassToggle.checked;
            });
        }
        if (lowpassToggle && lowpassValue) {
            lowpassToggle.addEventListener('change', () => {
                lowpassValue.disabled = !lowpassToggle.checked;
            });
        }

        if (videoDenoiseToggle && videoDenoiseWrap && videoDenoiseStrength) {
            videoDenoiseToggle.addEventListener('change', () => {
                const enabled = videoDenoiseToggle.checked;
                videoDenoiseWrap.hidden = !enabled;
                if (!enabled) {
                    videoDenoiseStrength.value = '1.6';
                    updateVideoDenoiseDisplay();
                }
            });
            videoDenoiseStrength.addEventListener('input', () => {
                updateVideoDenoiseDisplay();
            });
        }

        if (outputSelect) {
            outputSelect.innerHTML = '';
            formatInfo.outputFormats.forEach((option, idx) => {
                const opt = document.createElement('option');
                opt.value = option.value;
                opt.textContent = option.label;
                if (idx === 0) opt.selected = true;
                outputSelect.appendChild(opt);
            });
            const updateHelp = () => {
                if (!outputHelp) return;
                const selected = formatInfo.outputFormats.find(o => o.value === outputSelect.value);
                outputHelp.textContent = selected ? selected.help : '';
            };
            outputSelect.addEventListener('change', updateHelp);
            updateHelp();
        }
    }

    function gatherSettingsPayload() {
        if (!currentFormat) return null;
        if (!currentSettingsScope) {
            currentSettingsScope = settingsWrapper;
        }
        if (!currentSettingsScope) return null;
        const scope = currentSettingsScope;
        const get = role => scope.querySelector(`[data-role="${role}"]`);
        const payload = {
            extension: currentFormat.backendKey,
            originalExtension: currentFormat.extension,
            kind: currentFormat.kind,
            profile: (get('profile-select') || { value: 'custom' }).value,
            noiseReduction: Number((get('noise-reduction') || { value: '12' }).value),
            residualFloor: Number((get('residual-floor') || { value: '-50' }).value),
            temporalSmoothing: Number((get('temporal-smoothing') || { value: '18' }).value) / 10,
            frequencySmoothing: Number((get('frequency-smoothing') || { value: '8' }).value),
            outputFormat: (get('output-format') || { value: 'wav' }).value,
            highpassEnabled: !!(get('highpass-toggle') && get('highpass-toggle').checked),
            highpassCutoff: Number((get('highpass-value') || { value: '120' }).value),
            lowpassEnabled: !!(get('lowpass-toggle') && get('lowpass-toggle').checked),
            lowpassCutoff: Number((get('lowpass-value') || { value: '15000' }).value)
        };
        if (currentFormat.kind === 'video') {
            payload.preserveVideo = !!(get('preserve-video') && get('preserve-video').checked);
            payload.videoDenoise = !!(get('video-denoise') && get('video-denoise').checked);
            payload.videoDenoiseStrength = Number((get('video-denoise-strength') || { value: '1.6' }).value);
        }
        return payload;
    }

    function handleFileSelected(file) {
        const formatInfo = selectFormatInfo(file);
        currentFile = file;
        currentFormat = formatInfo;
        clearLog();
        hideDownload();
        if (!formatInfo) {
            detailsEl.textContent = `${file.name} — unsupported media type (${file.type || 'unknown'})`;
            settingsWrapper.innerHTML = '';
            processBtn.disabled = true;
            resetBtn.disabled = false;
            appendLog('Unsupported media type. Please choose a common audio or video format.');
            return;
        }
        describeFile(file, formatInfo);
        renderSettings(formatInfo);
        processBtn.disabled = false;
        resetBtn.disabled = false;
        appendLog(`Ready to process ${file.name} (${formatInfo.label}).`);
    }

    async function processFile() {
        if (!currentFile || !currentFormat) {
            return;
        }
        const settings = gatherSettingsPayload();
        if (!settings) {
            appendLog('Settings could not be collected.');
            return;
        }
        clearLog();
        appendLog('Preparing upload...');
        processBtn.disabled = true;
        resetBtn.disabled = true;
        hideDownload();
        try {
            const body = new FormData();
            body.append('media_file', currentFile);
            body.append('settings', JSON.stringify(settings));
            appendLog('Uploading file to server for processing...');
            const response = await fetch('/api/av/noise-reduction', { method: 'POST', body });
            if (!response.ok) {
                let detail = response.statusText;
                try {
                    const data = await response.json();
                    if (data && typeof data.detail === 'object' && data.detail !== null) {
                        if (Array.isArray(data.detail.log)) {
                            data.detail.log.forEach(line => appendLog(line));
                        }
                        detail = data.detail.message || data.detail.detail || detail;
                    } else if (data && data.detail) {
                        detail = data.detail;
                    } else if (data && Array.isArray(data.log)) {
                        data.log.forEach(line => appendLog(line));
                        detail = data.message || detail;
                    } else {
                        detail = JSON.stringify(data);
                    }
                } catch (err) {
                    detail = await response.text();
                }
                appendLog(`Processing failed: ${detail}`);
                return;
            }
            const result = await response.json();
            if (Array.isArray(result.log)) {
                result.log.forEach(line => appendLog(line));
            } else if (result.log) {
                appendLog(String(result.log));
            }
            if (result.download_token) {
                downloadLink.href = `/api/av/noise-reduction/${result.download_token}`;
                if (result.download_name) {
                    downloadLink.download = result.download_name;
                }
                downloadWrap.classList.remove('hidden');
                appendLog('Processing complete. Download is ready.');
            }
        } catch (error) {
            appendLog(`Unexpected error: ${error.message}`);
        } finally {
            processBtn.disabled = !currentFile;
            resetBtn.disabled = !currentFile;
        }
    }

    function onDrop(event) {
        event.preventDefault();
        dropZone.classList.remove('hover');
        const files = event.dataTransfer?.files;
        if (!files || !files.length) return;
        handleFileSelected(files[0]);
    }

    function onDrag(event) {
        event.preventDefault();
        dropZone.classList.add('hover');
    }

    function onDragLeave(event) {
        event.preventDefault();
        dropZone.classList.remove('hover');
    }

    dropZone.addEventListener('dragenter', onDrag);
    dropZone.addEventListener('dragover', onDrag);
    dropZone.addEventListener('dragleave', onDragLeave);
    dropZone.addEventListener('drop', onDrop);
    dropZone.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            fileInput.click();
        }
    });
    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', () => {
        const file = fileInput.files && fileInput.files[0];
        if (file) {
            handleFileSelected(file);
        }
    });

    processBtn.addEventListener('click', event => {
        event.preventDefault();
        processFile();
    });

    resetBtn.addEventListener('click', event => {
        event.preventDefault();
        resetState();
    });

    resetState();
})();
