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

    const AAC_BITRATE_OPTIONS = [128, 160, 192, 224, 256, 320];
    const DEFAULT_AAC_BITRATE = 192;
    const VIDEO_PRESET_OPTIONS = [
        { value: 'ultrafast', label: 'Ultrafast' },
        { value: 'superfast', label: 'Superfast' },
        { value: 'veryfast', label: 'Very fast' },
        { value: 'faster', label: 'Faster' },
        { value: 'fast', label: 'Fast' },
        { value: 'medium', label: 'Medium' },
        { value: 'slow', label: 'Slow' },
        { value: 'slower', label: 'Slower' },
        { value: 'veryslow', label: 'Very slow' }
    ];
    const DEFAULT_VIDEO_PRESET = 'medium';

    const createAudioBitrateConfig = () => ({
        options: AAC_BITRATE_OPTIONS.slice(),
        default: DEFAULT_AAC_BITRATE
    });

    const createVideoQualityConfig = () => ({
        min: 16,
        max: 30,
        step: 1,
        defaultCrf: 20,
        presets: VIDEO_PRESET_OPTIONS.map(option => ({ ...option })),
        defaultPreset: DEFAULT_VIDEO_PRESET
    });

    const FORMAT_LIBRARY = {
        mp3: {
            kind: 'audio',
            label: 'MP3 audio',
            backendKey: 'mp3',
            outputFormats: [
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Best for editing or archiving.' },
                { value: 'flac', label: 'FLAC (lossless)', help: 'Keeps file smaller while lossless.' },
                {
                    value: 'm4a',
                    label: 'M4A (AAC)',
                    help: 'Good balance for sharing.',
                    audioBitrate: createAudioBitrateConfig()
                }
            ]
        },
        wav: {
            kind: 'audio',
            label: 'WAV audio',
            backendKey: 'wav',
            outputFormats: [
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Preserves full quality.' },
                { value: 'flac', label: 'FLAC (lossless)', help: 'Compress without losing quality.' },
                {
                    value: 'm4a',
                    label: 'M4A (AAC)',
                    help: 'Smaller file for distribution.',
                    audioBitrate: createAudioBitrateConfig()
                }
            ]
        },
        flac: {
            kind: 'audio',
            label: 'FLAC audio',
            backendKey: 'flac',
            outputFormats: [
                { value: 'flac', label: 'FLAC (lossless)', help: 'Keep as lossless FLAC.' },
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Great for further processing.' },
                {
                    value: 'm4a',
                    label: 'M4A (AAC)',
                    help: 'Encode to AAC for compatibility.',
                    audioBitrate: createAudioBitrateConfig()
                }
            ]
        },
        ogg: {
            kind: 'audio',
            label: 'Ogg/Vorbis audio',
            backendKey: 'ogg',
            outputFormats: [
                { value: 'flac', label: 'FLAC (lossless)', help: 'Ideal for mastering.' },
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Full quality wave file.' },
                {
                    value: 'm4a',
                    label: 'M4A (AAC)',
                    help: 'Convert for players that do not support OGG.',
                    audioBitrate: createAudioBitrateConfig()
                }
            ]
        },
        m4a: {
            kind: 'audio',
            label: 'M4A audio',
            backendKey: 'm4a',
            outputFormats: [
                {
                    value: 'm4a',
                    label: 'M4A (AAC)',
                    help: 'Keep the MPEG-4 container.',
                    audioBitrate: createAudioBitrateConfig()
                },
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Export an uncompressed master.' },
                { value: 'flac', label: 'FLAC (lossless)', help: 'Store as lossless FLAC.' }
            ]
        },
        aac: {
            kind: 'audio',
            label: 'AAC audio',
            backendKey: 'aac',
            outputFormats: [
                {
                    value: 'm4a',
                    label: 'M4A (AAC)',
                    help: 'Keep AAC audio in M4A container.',
                    audioBitrate: createAudioBitrateConfig()
                },
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
                {
                    value: 'm4a',
                    label: 'M4A (AAC)',
                    help: 'Convert to AAC for compatibility.',
                    audioBitrate: createAudioBitrateConfig()
                }
            ]
        },
        mp4: {
            kind: 'video',
            label: 'MP4 video',
            backendKey: 'mp4',
            outputFormats: [
                {
                    value: 'mp4',
                    label: 'MP4 (H.264 + AAC)',
                    help: 'Universal compatibility.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'mkv',
                    label: 'MKV (H.264 + AAC)',
                    help: 'Matroska container with AAC audio.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'avi',
                    label: 'AVI (H.264 + AAC)',
                    help: 'Legacy AVI container output.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                }
            ]
        },
        mov: {
            kind: 'video',
            label: 'QuickTime/MOV video',
            backendKey: 'mov',
            outputFormats: [
                {
                    value: 'mov',
                    label: 'MOV (H.264 + AAC)',
                    help: 'QuickTime compatible output.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'mp4',
                    label: 'MP4 (H.264 + AAC)',
                    help: 'Widely supported mp4 container.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'mkv',
                    label: 'MKV (H.264 + AAC)',
                    help: 'Matroska container.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'avi',
                    label: 'AVI (H.264 + AAC)',
                    help: 'Export to AVI for legacy workflows.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                }
            ]
        },
        mkv: {
            kind: 'video',
            label: 'Matroska video',
            backendKey: 'mkv',
            outputFormats: [
                {
                    value: 'mkv',
                    label: 'MKV (H.264 + AAC)',
                    help: 'Matroska container output.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'mp4',
                    label: 'MP4 (H.264 + AAC)',
                    help: 'Export as MP4 for portability.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'avi',
                    label: 'AVI (H.264 + AAC)',
                    help: 'Legacy AVI container output.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                }
            ]
        },
        avi: {
            kind: 'video',
            label: 'AVI video',
            backendKey: 'avi',
            outputFormats: [
                {
                    value: 'avi',
                    label: 'AVI (H.264 + AAC)',
                    help: 'Keep the AVI container with refreshed codecs.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'mp4',
                    label: 'MP4 (H.264 + AAC)',
                    help: 'Transcode to MP4 for modern playback.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'mkv',
                    label: 'MKV (H.264 + AAC)',
                    help: 'Store in Matroska container.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                }
            ]
        },
        webm: {
            kind: 'video',
            label: 'WebM video',
            backendKey: 'webm',
            outputFormats: [
                {
                    value: 'mkv',
                    label: 'MKV (H.264 + AAC)',
                    help: 'Rewrap with H.264 + AAC output.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'mp4',
                    label: 'MP4 (H.264 + AAC)',
                    help: 'Convert for wider device support.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'avi',
                    label: 'AVI (H.264 + AAC)',
                    help: 'Export to AVI for compatibility with legacy systems.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                }
            ]
        },
        'generic-audio': {
            kind: 'audio',
            label: 'Audio stream',
            backendKey: 'generic-audio',
            outputFormats: [
                { value: 'wav', label: 'WAV (16-bit PCM)', help: 'Safe uncompressed audio output.' },
                { value: 'flac', label: 'FLAC (lossless)', help: 'Lossless but smaller than WAV.' },
                {
                    value: 'm4a',
                    label: 'M4A (AAC)',
                    help: 'Compressed output for sharing.',
                    audioBitrate: createAudioBitrateConfig()
                }
            ]
        },
        'generic-video': {
            kind: 'video',
            label: 'Video stream',
            backendKey: 'generic-video',
            outputFormats: [
                {
                    value: 'mp4',
                    label: 'MP4 (H.264 + AAC)',
                    help: 'Standard MP4 output.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'avi',
                    label: 'AVI (H.264 + AAC)',
                    help: 'Legacy AVI container output.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                },
                {
                    value: 'mkv',
                    label: 'MKV (H.264 + AAC)',
                    help: 'Matroska container output.',
                    audioBitrate: createAudioBitrateConfig(),
                    videoQuality: createVideoQualityConfig()
                }
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
        const audioBitrateField = scope.querySelector('[data-role="audio-bitrate-field"]');
        const audioBitrateSelect = scope.querySelector('[data-role="audio-bitrate"]');
        const videoCrfField = scope.querySelector('[data-role="video-crf-field"]');
        const videoCrfRange = scope.querySelector('[data-role="video-crf"]');
        const videoCrfDisplay = scope.querySelector('[data-role="video-crf-display"]');
        const videoPresetField = scope.querySelector('[data-role="video-preset-field"]');
        const videoPresetSelect = scope.querySelector('[data-role="video-preset"]');

        const formatBitrateValue = kbps => `${kbps}k`;
        const formatBitrateLabel = kbps => `${kbps} kbps`;

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
        const updateVideoCrfDisplay = () => {
            if (videoCrfDisplay && videoCrfRange) {
                videoCrfDisplay.textContent = `CRF ${videoCrfRange.value}`;
            }
        };

        const updateVideoEncodeControlsState = () => {
            if (!videoCrfRange && !videoPresetSelect) return;
            const shouldEncode = !preserveVideo || !preserveVideo.checked || (videoDenoiseToggle && videoDenoiseToggle.checked);
            const disableVideoControls = !shouldEncode;
            if (videoCrfRange) {
                videoCrfRange.disabled = disableVideoControls || (videoCrfField && videoCrfField.hidden);
            }
            if (videoPresetSelect) {
                videoPresetSelect.disabled = disableVideoControls || (videoPresetField && videoPresetField.hidden);
            }
        };

        const applyOutputFormatOptions = () => {
            if (!outputSelect || !Array.isArray(formatInfo.outputFormats)) {
                if (audioBitrateField) audioBitrateField.hidden = true;
                if (videoCrfField) videoCrfField.hidden = true;
                if (videoPresetField) videoPresetField.hidden = true;
                updateVideoEncodeControlsState();
                return;
            }
            const selected = formatInfo.outputFormats.find(option => option.value === outputSelect.value);
            if (!selected) {
                if (audioBitrateField) audioBitrateField.hidden = true;
                if (videoCrfField) videoCrfField.hidden = true;
                if (videoPresetField) videoPresetField.hidden = true;
                updateVideoEncodeControlsState();
                return;
            }

            if (audioBitrateField && audioBitrateSelect) {
                const config = selected.audioBitrate;
                if (config && Array.isArray(config.options) && config.options.length) {
                    const previous = audioBitrateSelect.value;
                    audioBitrateSelect.innerHTML = '';
                    config.options.forEach(kbps => {
                        const opt = document.createElement('option');
                        const value = formatBitrateValue(kbps);
                        opt.value = value;
                        opt.textContent = formatBitrateLabel(kbps);
                        audioBitrateSelect.appendChild(opt);
                    });
                    const validValues = config.options.map(formatBitrateValue);
                    const defaultValue = formatBitrateValue(config.default ?? config.options[0]);
                    audioBitrateSelect.value = validValues.includes(previous) ? previous : defaultValue;
                    audioBitrateField.hidden = false;
                } else {
                    audioBitrateField.hidden = true;
                }
            }

            if (videoCrfField && videoCrfRange && videoCrfDisplay) {
                const quality = selected.videoQuality;
                if (quality) {
                    const previous = Number(videoCrfRange.value);
                    const min = Number.isFinite(quality.min) ? Number(quality.min) : 16;
                    const max = Number.isFinite(quality.max) ? Number(quality.max) : 30;
                    const step = Number.isFinite(quality.step) ? Number(quality.step) : 1;
                    videoCrfRange.min = String(min);
                    videoCrfRange.max = String(max);
                    videoCrfRange.step = String(step);
                    let nextValue = Number.isFinite(previous) && previous >= min && previous <= max
                        ? previous
                        : Number.isFinite(quality.defaultCrf) ? Number(quality.defaultCrf) : Math.round((min + max) / 2);
                    nextValue = Math.min(Math.max(nextValue, min), max);
                    videoCrfRange.value = String(nextValue);
                    updateVideoCrfDisplay();
                    videoCrfField.hidden = false;
                } else {
                    videoCrfField.hidden = true;
                }
            }

            if (videoPresetField && videoPresetSelect) {
                const quality = selected.videoQuality;
                if (quality && Array.isArray(quality.presets) && quality.presets.length) {
                    const previous = videoPresetSelect.value;
                    videoPresetSelect.innerHTML = '';
                    quality.presets.forEach(preset => {
                        const opt = document.createElement('option');
                        opt.value = preset.value;
                        opt.textContent = preset.label;
                        videoPresetSelect.appendChild(opt);
                    });
                    const validValues = quality.presets.map(preset => preset.value);
                    let defaultPreset = quality.defaultPreset && validValues.includes(quality.defaultPreset)
                        ? quality.defaultPreset
                        : (validValues.includes(DEFAULT_VIDEO_PRESET) ? DEFAULT_VIDEO_PRESET : quality.presets[0].value);
                    videoPresetSelect.value = validValues.includes(previous) ? previous : defaultPreset;
                    videoPresetField.hidden = false;
                } else {
                    videoPresetField.hidden = true;
                }
            }

            updateVideoEncodeControlsState();
        };

        updateNoiseDisplay();
        updateFloorDisplay();
        updateTemporalDisplay();
        updateFreqDisplay();
        updateVideoDenoiseDisplay();
        updateVideoCrfDisplay();

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
                updateVideoEncodeControlsState();
            });
            videoDenoiseStrength.addEventListener('input', () => {
                updateVideoDenoiseDisplay();
            });
        }

        if (preserveVideo) {
            preserveVideo.addEventListener('change', () => {
                updateVideoEncodeControlsState();
            });
        }

        if (videoCrfRange) {
            videoCrfRange.addEventListener('input', () => {
                updateVideoCrfDisplay();
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
            const updateOutputDetails = () => {
                if (outputHelp) {
                    const selected = formatInfo.outputFormats.find(o => o.value === outputSelect.value);
                    outputHelp.textContent = selected ? selected.help : '';
                }
                applyOutputFormatOptions();
            };
            outputSelect.addEventListener('change', updateOutputDetails);
            updateOutputDetails();
        } else {
            applyOutputFormatOptions();
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
        const audioBitrateControl = get('audio-bitrate');
        if (audioBitrateControl && audioBitrateControl.value) {
            payload.audioBitrate = audioBitrateControl.value;
        }
        if (currentFormat.kind === 'video') {
            payload.preserveVideo = !!(get('preserve-video') && get('preserve-video').checked);
            payload.videoDenoise = !!(get('video-denoise') && get('video-denoise').checked);
            payload.videoDenoiseStrength = Number((get('video-denoise-strength') || { value: '1.6' }).value);
            const videoCrfControl = get('video-crf');
            if (videoCrfControl && videoCrfControl.value) {
                payload.videoCrf = Number(videoCrfControl.value);
            }
            const videoPresetControl = get('video-preset');
            if (videoPresetControl && videoPresetControl.value) {
                payload.videoPreset = videoPresetControl.value;
            }
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
    dropZone.addEventListener('click', event => {
        const target = event.target;
        if (target === fileInput || (target && typeof target.closest === 'function' && target.closest('input[type="file"]'))) {
            return;
        }
        fileInput.click();
    });

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
