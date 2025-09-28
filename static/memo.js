(function () {
  'use strict';

  const state = {
    memos: [],
    isTranscribing: false
  };

  const recordButton = document.getElementById('memo-record-btn');
  const liveTranscriptEl = document.getElementById('memo-live-transcript');
  const manualInput = document.getElementById('memo-manual-input');
  const manualSaveButton = document.getElementById('memo-manual-save');
  const statusEl = document.getElementById('memo-status');
  const transcriptionForm = document.getElementById('memo-transcription-form');
  const transcriptionStatusEl = document.getElementById('memo-transcription-status');
  const transcriptionResultEl = document.getElementById('memo-transcription-result');
  const transcriptionFileInput = document.getElementById('memo-file-input');
  const transcriptionUrlInput = document.getElementById('memo-url-input');
  const transcriptionSubmitButton = document.getElementById('memo-transcription-submit');
  const memoListEl = document.getElementById('memo-list');

  const cameraSection = document.getElementById('memo-camera-section');
  const cameraPreviewEl = document.getElementById('memo-camera-preview');
  const cameraStartButton = document.getElementById('memo-camera-start');
  const cameraStopButton = document.getElementById('memo-camera-stop');
  const cameraStatusEl = document.getElementById('memo-camera-status');
  const photoCanvas = document.getElementById('memo-photo-canvas');
  const photoCaptureButton = document.getElementById('memo-photo-capture');
  const photoSaveButton = document.getElementById('memo-photo-save');
  const photoPreviewImage = document.getElementById('memo-photo-preview');
  const photoMetaEl = document.getElementById('memo-photo-meta');
  const qrToggleButton = document.getElementById('memo-qr-toggle');
  const qrSaveButton = document.getElementById('memo-qr-save');
  const qrResultEl = document.getElementById('memo-qr-result');
  const videoRecordButton = document.getElementById('memo-video-record');
  const videoStopButton = document.getElementById('memo-video-stop');
  const videoSaveButton = document.getElementById('memo-video-save');
  const videoPreviewEl = document.getElementById('memo-video-preview');
  const videoMetaEl = document.getElementById('memo-video-meta');

  const cameraState = {
    stream: null,
    startPromise: null,
    barcodeDetector: null,
    qrActive: false,
    qrLastValue: '',
    qrLastFormat: '',
    qrScanTimeoutId: null,
    photoBlob: null,
    photoPreviewUrl: null,
    recordedChunks: [],
    recorder: null,
    recorderMimeType: '',
    recordingCancelled: false,
    videoBlob: null,
    videoPreviewUrl: null,
    cameraStatusTimeoutId: null
  };

  const supportsBarcodeDetector = typeof window !== 'undefined' && typeof window.BarcodeDetector === 'function';
  const supportsMediaRecorder = typeof window !== 'undefined' && typeof window.MediaRecorder === 'function';

  let statusTimeoutId = null;
  let transcriptionStatusTimeoutId = null;

  async function copyTextToClipboard(text) {
    const value = typeof text === 'string' ? text : '';
    if (!value) {
      return false;
    }

    if (typeof navigator !== 'undefined' && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      try {
        await navigator.clipboard.writeText(value);
        return true;
      } catch (error) {
        console.error('navigator.clipboard.writeText failed', error);
      }
    }

    if (!document.body) {
      return false;
    }

    try {
      const textarea = document.createElement('textarea');
      textarea.value = value;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'absolute';
      textarea.style.left = '-9999px';
      textarea.style.top = '0';
      textarea.style.fontSize = '16px';

      const activeElement = document.activeElement;
      const selection = document.getSelection();
      const selectedRange = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null;

      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      textarea.setSelectionRange(0, textarea.value.length);

      const successful = document.execCommand('copy');

      document.body.removeChild(textarea);

      if (selectedRange && selection) {
        selection.removeAllRanges();
        selection.addRange(selectedRange);
      } else if (selection) {
        selection.removeAllRanges();
      }

      if (activeElement && typeof activeElement.focus === 'function') {
        activeElement.focus();
      }

      return successful;
    } catch (error) {
      console.error('Fallback clipboard copy failed', error);
      return false;
    }
  }

  function formatMemoTime(isoString) {
    if (!isoString) {
      return '';
    }
    try {
      if (typeof window.formatDutchTime === 'function') {
        return window.formatDutchTime(isoString);
      }
      return new Date(isoString).toLocaleString('nl-NL');
    } catch (error) {
      return isoString;
    }
  }

  function formatFileSize(bytes) {
    const value = typeof bytes === 'number' && Number.isFinite(bytes) ? Math.max(bytes, 0) : 0;
    if (value === 0) {
      return '0 B';
    }

    const units = ['B', 'KB', 'MB', 'GB'];
    const exponent = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
    const size = value / (1024 ** exponent);
    return `${size.toFixed(size >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
  }

  function formatTimestampForName() {
    const now = new Date();
    const parts = [
      now.getFullYear(),
      String(now.getMonth() + 1).padStart(2, '0'),
      String(now.getDate()).padStart(2, '0'),
      String(now.getHours()).padStart(2, '0'),
      String(now.getMinutes()).padStart(2, '0'),
      String(now.getSeconds()).padStart(2, '0')
    ];
    return `${parts[0]}${parts[1]}${parts[2]}-${parts[3]}${parts[4]}${parts[5]}`;
  }

  function showStatus(message, type = 'info') {
    if (!statusEl) {
      return;
    }

    statusEl.textContent = message;
    statusEl.classList.remove('status-success', 'status-error', 'status-warning');
    statusEl.style.display = 'block';

    const className = type === 'success'
      ? 'status-success'
      : type === 'error'
        ? 'status-error'
        : type === 'warning'
          ? 'status-warning'
          : '';

    if (className) {
      statusEl.classList.add(className);
    }

    if (statusTimeoutId) {
      window.clearTimeout(statusTimeoutId);
    }

    statusTimeoutId = window.setTimeout(() => {
      statusEl.style.display = 'none';
      statusEl.classList.remove('status-success', 'status-error', 'status-warning');
      statusTimeoutId = null;
    }, 5000);
  }

  function clearStatus() {
    if (!statusEl) {
      return;
    }
    statusEl.style.display = 'none';
    statusEl.textContent = '';
    statusEl.classList.remove('status-success', 'status-error', 'status-warning');
    if (statusTimeoutId) {
      window.clearTimeout(statusTimeoutId);
      statusTimeoutId = null;
    }
  }

  function showCameraStatus(message, type = 'info') {
    if (!cameraStatusEl) {
      return;
    }

    cameraStatusEl.textContent = message;
    cameraStatusEl.classList.remove('status-success', 'status-error', 'status-warning');
    cameraStatusEl.style.display = message ? 'block' : 'none';

    const className = type === 'success'
      ? 'status-success'
      : type === 'error'
        ? 'status-error'
        : type === 'warning'
          ? 'status-warning'
          : '';

    if (className) {
      cameraStatusEl.classList.add(className);
    }

    window.clearTimeout(cameraState.cameraStatusTimeoutId);
    cameraState.cameraStatusTimeoutId = window.setTimeout(() => {
      if (cameraStatusEl) {
        cameraStatusEl.style.display = 'none';
        cameraStatusEl.textContent = '';
        cameraStatusEl.classList.remove('status-success', 'status-error', 'status-warning');
      }
      cameraState.cameraStatusTimeoutId = null;
    }, 6000);
  }

  function clearCameraStatus() {
    if (cameraStatusEl) {
      cameraStatusEl.textContent = '';
      cameraStatusEl.style.display = 'none';
      cameraStatusEl.classList.remove('status-success', 'status-error', 'status-warning');
    }
    if (cameraState.cameraStatusTimeoutId) {
      window.clearTimeout(cameraState.cameraStatusTimeoutId);
      cameraState.cameraStatusTimeoutId = null;
    }
  }

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      if (!(blob instanceof Blob)) {
        reject(new Error('Ongeldig bestand.'));
        return;
      }
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = reader.result;
        if (typeof result === 'string') {
          const commaIndex = result.indexOf(',');
          resolve(commaIndex >= 0 ? result.slice(commaIndex + 1) : result);
        } else {
          reject(new Error('Kon media niet converteren.'));
        }
      };
      reader.onerror = () => reject(new Error('Kon media niet converteren.'));
      reader.readAsDataURL(blob);
    });
  }

  function getExtensionFromMime(mimeType) {
    if (!mimeType || typeof mimeType !== 'string') {
      return '';
    }
    const lower = mimeType.toLowerCase();
    if (lower.includes('jpeg')) { return 'jpg'; }
    if (lower.includes('png')) { return 'png'; }
    if (lower.includes('webp')) { return 'webp'; }
    if (lower.includes('mp4')) { return 'mp4'; }
    if (lower.includes('ogg')) { return 'ogg'; }
    if (lower.includes('webm')) { return 'webm'; }
    return '';
  }

  function tryParseUrl(value) {
    if (!value || typeof value !== 'string') {
      return null;
    }
    try {
      return new URL(value);
    } catch (error) {
      return null;
    }
  }

  function ensureBarcodeDetector() {
    if (!supportsBarcodeDetector) {
      return null;
    }
    if (!cameraState.barcodeDetector) {
      try {
        cameraState.barcodeDetector = new window.BarcodeDetector({
          formats: ['qr_code', 'aztec', 'data_matrix']
        });
      } catch (error) {
        console.error('Failed to initialise BarcodeDetector', error);
        cameraState.barcodeDetector = null;
      }
    }
    return cameraState.barcodeDetector;
  }

  function updateCameraButtons(hasStream) {
    if (cameraStartButton) {
      cameraStartButton.disabled = Boolean(hasStream);
    }
    if (cameraStopButton) {
      cameraStopButton.disabled = !hasStream;
    }
    if (photoCaptureButton) {
      photoCaptureButton.disabled = !hasStream;
    }
    if (photoSaveButton) {
      photoSaveButton.disabled = !cameraState.photoBlob;
    }
    if (qrToggleButton) {
      qrToggleButton.disabled = !hasStream || !supportsBarcodeDetector;
      if (!supportsBarcodeDetector) {
        qrToggleButton.textContent = 'QR-scanner niet ondersteund';
      }
    }
    if (qrSaveButton) {
      qrSaveButton.disabled = !cameraState.qrLastValue;
    }
    const isRecording = cameraState.recorder && cameraState.recorder.state === 'recording';
    if (videoRecordButton) {
      videoRecordButton.disabled = !hasStream || !supportsMediaRecorder || isRecording;
      if (!supportsMediaRecorder) {
        videoRecordButton.textContent = 'Video niet ondersteund';
      }
    }
    if (videoStopButton) {
      videoStopButton.disabled = !isRecording;
    }
    if (videoSaveButton) {
      videoSaveButton.disabled = !cameraState.videoBlob;
    }
  }

  async function ensureCameraStream() {
    if (cameraState.stream) {
      updateCameraButtons(true);
      return cameraState.stream;
    }

    if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== 'function') {
      showCameraStatus('Camera wordt niet ondersteund op dit apparaat.', 'error');
      return null;
    }

    if (cameraState.startPromise) {
      return cameraState.startPromise;
    }

    clearCameraStatus();

    const constraints = {
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1280 },
        height: { ideal: 720 }
      },
      audio: true
    };

    cameraState.startPromise = navigator.mediaDevices.getUserMedia(constraints)
      .then((stream) => {
        cameraState.stream = stream;
        if (cameraPreviewEl) {
          cameraPreviewEl.srcObject = stream;
          const playPromise = cameraPreviewEl.play();
          if (playPromise && typeof playPromise.catch === 'function') {
            playPromise.catch(() => undefined);
          }
        }
        updateCameraButtons(true);
        showCameraStatus('Camera geactiveerd. Richt je toestel op het gewenste onderwerp.', 'success');
        return stream;
      })
      .catch((error) => {
        let message = 'Kon de camera niet starten.';
        if (error && (error.name === 'NotAllowedError' || error.name === 'SecurityError')) {
          message = 'Toegang tot de camera geweigerd.';
        } else if (error && error.name === 'NotFoundError') {
          message = 'Geen camera gevonden op dit apparaat.';
        }
        showCameraStatus(message, 'error');
        throw error;
      })
      .finally(() => {
        cameraState.startPromise = null;
      });

    return cameraState.startPromise;
  }

  function stopQrScanTimer() {
    if (cameraState.qrScanTimeoutId) {
      window.clearTimeout(cameraState.qrScanTimeoutId);
      cameraState.qrScanTimeoutId = null;
    }
  }

  function stopCameraStream() {
    if (cameraState.recorder && cameraState.recorder.state === 'recording') {
      stopVideoRecording(true);
    }
    stopQrScan({ keepResult: true });

    const stream = cameraState.stream;
    if (stream) {
      stream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (error) {
          console.warn('Kon cameratrack niet stoppen', error);
        }
      });
    }

    cameraState.stream = null;
    if (cameraPreviewEl) {
      cameraPreviewEl.pause();
      cameraPreviewEl.srcObject = null;
    }
    updateCameraButtons(false);
    showCameraStatus('Camera gestopt.', 'info');
  }

  function resetPhotoPreview() {
    if (cameraState.photoPreviewUrl) {
      window.URL.revokeObjectURL(cameraState.photoPreviewUrl);
      cameraState.photoPreviewUrl = null;
    }
    if (photoPreviewImage) {
      photoPreviewImage.hidden = true;
      photoPreviewImage.removeAttribute('src');
    }
    if (photoMetaEl) {
      photoMetaEl.textContent = '';
    }
    cameraState.photoBlob = null;
    if (photoSaveButton) {
      photoSaveButton.disabled = true;
    }
  }

  function updatePhotoPreview(blob, width, height) {
    if (!photoPreviewImage) {
      return;
    }
    if (cameraState.photoPreviewUrl) {
      window.URL.revokeObjectURL(cameraState.photoPreviewUrl);
      cameraState.photoPreviewUrl = null;
    }
    const previewUrl = window.URL.createObjectURL(blob);
    cameraState.photoPreviewUrl = previewUrl;
    photoPreviewImage.src = previewUrl;
    photoPreviewImage.hidden = false;
    if (photoMetaEl) {
      const parts = [];
      if (width && height) {
        parts.push(`${width}×${height}px`);
      }
      parts.push(`${formatFileSize(blob.size)} • ${blob.type || 'image/jpeg'}`);
      photoMetaEl.textContent = parts.join(' — ');
    }
    if (photoSaveButton) {
      photoSaveButton.disabled = false;
    }
  }

  async function capturePhoto() {
    if (!photoCaptureButton) {
      return;
    }

    try {
      photoCaptureButton.disabled = true;
      const stream = await ensureCameraStream();
      if (!stream || !cameraPreviewEl || !photoCanvas) {
        throw new Error('Camera niet beschikbaar.');
      }

      if (cameraPreviewEl.readyState < 2) {
        await new Promise((resolve) => {
          cameraPreviewEl.addEventListener('loadeddata', resolve, { once: true });
        });
      }

      const width = cameraPreviewEl.videoWidth || 1280;
      const height = cameraPreviewEl.videoHeight || 720;
      photoCanvas.width = width;
      photoCanvas.height = height;
      const context = photoCanvas.getContext('2d', { willReadFrequently: true });
      if (!context) {
        throw new Error('Deze browser ondersteunt geen camerafoto.');
      }
      context.drawImage(cameraPreviewEl, 0, 0, width, height);

      const blob = await new Promise((resolve, reject) => {
        try {
          photoCanvas.toBlob((result) => {
            if (result) {
              resolve(result);
            } else {
              reject(new Error('Kon de foto niet opslaan.'));
            }
          }, 'image/jpeg', 0.92);
        } catch (error) {
          reject(error);
        }
      });

      cameraState.photoBlob = blob;
      updatePhotoPreview(blob, width, height);
      updateCameraButtons(Boolean(cameraState.stream));
      showCameraStatus('Foto vastgelegd. Controleer het voorbeeld en sla op als object.', 'success');
    } catch (error) {
      console.error('Failed to capture photo', error);
      resetPhotoPreview();
      showCameraStatus(error.message || 'Foto maken mislukt.', 'error');
    } finally {
      photoCaptureButton.disabled = !cameraState.stream;
    }
  }

  async function savePhoto() {
    if (!cameraState.photoBlob) {
      showCameraStatus('Maak eerst een foto voordat je opslaat.', 'warning');
      return;
    }

    if (photoSaveButton) {
      photoSaveButton.disabled = true;
      photoSaveButton.textContent = 'Opslaan…';
    }

    try {
      const base64 = await blobToBase64(cameraState.photoBlob);
      const mimeType = cameraState.photoBlob.type || 'image/jpeg';
      const extension = getExtensionFromMime(mimeType) || 'jpg';
      const payload = {
        object_type: 'file',
        object_name: `memo-foto-${formatTimestampForName()}.${extension}`,
        object_data: base64,
        file_size: cameraState.photoBlob.size,
        mime_type: mimeType,
        note: `Foto gemaakt via memo-camera op ${new Date().toLocaleString('nl-NL')}`
      };
      await saveSharedObject(payload);
    } catch (error) {
      if (error && error.message) {
        showCameraStatus(error.message, 'error');
      }
    } finally {
      if (photoSaveButton) {
        photoSaveButton.disabled = !cameraState.photoBlob;
        photoSaveButton.textContent = 'Object opslaan';
      }
    }
  }

  function updateQrResult(value, format) {
    cameraState.qrLastValue = value || '';
    cameraState.qrLastFormat = format || '';

    if (qrResultEl) {
      if (cameraState.qrLastValue) {
        const pieces = [];
        if (cameraState.qrLastFormat) {
          pieces.push(`[${cameraState.qrLastFormat.toUpperCase()}]`);
        }
        pieces.push(cameraState.qrLastValue);
        qrResultEl.textContent = pieces.join(' ');
      } else {
        qrResultEl.textContent = 'Nog geen QR-code gescand.';
      }
    }

    if (qrSaveButton) {
      qrSaveButton.disabled = !cameraState.qrLastValue;
    }
  }

  function scheduleQrScan() {
    stopQrScanTimer();
    if (!cameraState.qrActive) {
      return;
    }

    cameraState.qrScanTimeoutId = window.setTimeout(async () => {
      if (!cameraState.qrActive) {
        return;
      }

      if (!cameraPreviewEl || cameraPreviewEl.readyState < 2) {
        scheduleQrScan();
        return;
      }

      try {
        const detector = ensureBarcodeDetector();
        if (!detector) {
          throw new Error('QR-scanner niet beschikbaar.');
        }
        const results = await detector.detect(cameraPreviewEl);
        if (Array.isArray(results) && results.length) {
          const match = results[0];
          const rawValue = (match.rawValue || match.displayValue || '').trim();
          if (rawValue) {
            cameraState.qrActive = false;
            updateQrResult(rawValue, match.format || 'qr');
            if (qrToggleButton) {
              qrToggleButton.textContent = 'QR-scan starten';
            }
            showCameraStatus('QR-code gevonden.', 'success');
            updateCameraButtons(Boolean(cameraState.stream));
            stopQrScanTimer();
            return;
          }
        }
      } catch (error) {
        console.error('QR scan failed', error);
        cameraState.qrActive = false;
        if (qrToggleButton) {
          qrToggleButton.textContent = 'QR-scan starten';
        }
        showCameraStatus(error.message || 'QR-scanner onderbroken.', 'error');
        stopQrScanTimer();
        updateCameraButtons(Boolean(cameraState.stream));
        return;
      }

      scheduleQrScan();
    }, 350);
  }

  async function startQrScan() {
    if (!supportsBarcodeDetector) {
      showCameraStatus('QR-scanner wordt niet ondersteund in deze browser.', 'error');
      return;
    }

    const stream = await ensureCameraStream();
    if (!stream) {
      return;
    }

    const detector = ensureBarcodeDetector();
    if (!detector) {
      showCameraStatus('QR-scanner niet beschikbaar.', 'error');
      return;
    }

    cameraState.qrActive = true;
    updateQrResult('', '');
    if (qrToggleButton) {
      qrToggleButton.textContent = 'Stop QR-scan';
    }
    showCameraStatus('Scanner actief. Richt de camera op de QR-code.', 'info');
    scheduleQrScan();
  }

  function stopQrScan(options = {}) {
    const keepResult = Boolean(options.keepResult);
    cameraState.qrActive = false;
    stopQrScanTimer();
    if (!keepResult) {
      updateQrResult('', '');
    }
    if (qrToggleButton) {
      qrToggleButton.textContent = 'QR-scan starten';
      qrToggleButton.disabled = !cameraState.stream || !supportsBarcodeDetector;
    }
  }

  async function saveQrResult() {
    if (!cameraState.qrLastValue) {
      showCameraStatus('Er is nog geen QR-code gescand.', 'warning');
      return;
    }

    if (qrSaveButton) {
      qrSaveButton.disabled = true;
      qrSaveButton.textContent = 'Opslaan…';
    }

    try {
      const parsedUrl = tryParseUrl(cameraState.qrLastValue);
      const note = `QR-resultaat opgeslagen via memo-camera op ${new Date().toLocaleString('nl-NL')}`;
      if (parsedUrl) {
        await saveSharedObject({
          object_type: 'url',
          object_name: parsedUrl.hostname || 'QR-link',
          object_data: cameraState.qrLastValue,
          object_url: cameraState.qrLastValue,
          note
        });
      } else {
        const preview = cameraState.qrLastValue.length > 60
          ? `${cameraState.qrLastValue.slice(0, 60)}…`
          : cameraState.qrLastValue;
        await saveSharedObject({
          object_type: 'text',
          object_name: preview || 'QR-tekst',
          object_data: cameraState.qrLastValue,
          note
        });
      }
    } catch (error) {
      if (error && error.message) {
        showCameraStatus(error.message, 'error');
      }
    } finally {
      if (qrSaveButton) {
        qrSaveButton.disabled = !cameraState.qrLastValue;
        qrSaveButton.textContent = 'Resultaat opslaan';
      }
    }
  }

  function resetVideoPreview() {
    if (cameraState.videoPreviewUrl) {
      window.URL.revokeObjectURL(cameraState.videoPreviewUrl);
      cameraState.videoPreviewUrl = null;
    }
    if (videoPreviewEl) {
      videoPreviewEl.pause();
      videoPreviewEl.hidden = true;
      videoPreviewEl.removeAttribute('src');
      try {
        videoPreviewEl.load();
      } catch (error) {
        // Ignore load errors
      }
    }
    if (videoMetaEl) {
      videoMetaEl.textContent = '';
    }
    cameraState.videoBlob = null;
    if (videoSaveButton) {
      videoSaveButton.disabled = true;
    }
  }

  function getPreferredRecorderMimeType() {
    if (!supportsMediaRecorder || typeof window.MediaRecorder.isTypeSupported !== 'function') {
      return '';
    }
    const candidates = [
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp8,opus',
      'video/mp4;codecs=avc1.42E01E,mp4a.40.2',
      'video/webm'
    ];
    for (let i = 0; i < candidates.length; i += 1) {
      const candidate = candidates[i];
      try {
        if (window.MediaRecorder.isTypeSupported(candidate)) {
          return candidate;
        }
      } catch (error) {
        // Ignore capability errors and continue
      }
    }
    return '';
  }

  async function startVideoRecording() {
    if (!supportsMediaRecorder) {
      showCameraStatus('Video opnemen wordt niet ondersteund in deze browser.', 'error');
      return;
    }

    if (cameraState.recorder && cameraState.recorder.state === 'recording') {
      showCameraStatus('Er loopt al een opname.', 'warning');
      return;
    }

    const stream = await ensureCameraStream();
    if (!stream) {
      return;
    }

    resetVideoPreview();
    cameraState.recordedChunks = [];
    cameraState.recordingCancelled = false;

    const mimeType = getPreferredRecorderMimeType();

    try {
      const options = mimeType ? { mimeType } : undefined;
      const recorder = new window.MediaRecorder(stream, options);
      cameraState.recorder = recorder;
      cameraState.recorderMimeType = mimeType || recorder.mimeType || 'video/webm';

      recorder.addEventListener('dataavailable', (event) => {
        if (event.data && event.data.size && !cameraState.recordingCancelled) {
          cameraState.recordedChunks.push(event.data);
        }
      });

      recorder.addEventListener('stop', () => {
        const chunks = cameraState.recordedChunks;
        const wasCancelled = cameraState.recordingCancelled;
        if (!chunks.length || wasCancelled) {
          cameraState.recordedChunks = [];
          cameraState.recorder = null;
          cameraState.recorderMimeType = '';
          cameraState.recordingCancelled = false;
          updateCameraButtons(Boolean(cameraState.stream));
          if (wasCancelled) {
            showCameraStatus('Video-opname geannuleerd.', 'warning');
          }
          return;
        }

        const blob = new Blob(chunks, { type: cameraState.recorderMimeType || 'video/webm' });
        cameraState.videoBlob = blob;
        cameraState.recordedChunks = [];
        const previewUrl = window.URL.createObjectURL(blob);
        cameraState.videoPreviewUrl = previewUrl;
        if (videoPreviewEl) {
          videoPreviewEl.src = previewUrl;
          videoPreviewEl.hidden = false;
        }
        if (videoMetaEl) {
          videoMetaEl.textContent = `${formatFileSize(blob.size)} • ${cameraState.recorderMimeType || blob.type || 'video/webm'}`;
        }
        if (videoSaveButton) {
          videoSaveButton.disabled = false;
        }
        cameraState.recorder = null;
        cameraState.recorderMimeType = '';
        showCameraStatus('Video-opname klaar om op te slaan.', 'success');
        updateCameraButtons(Boolean(cameraState.stream));
      });

      recorder.addEventListener('error', (event) => {
        console.error('MediaRecorder error', event);
        showCameraStatus('Video-opname is gestopt door een fout.', 'error');
      });

      recorder.start();
      updateCameraButtons(true);
      if (videoStopButton) {
        videoStopButton.disabled = false;
      }
      showCameraStatus('Video-opname gestart. Tik op stop om te beëindigen.', 'info');
    } catch (error) {
      console.error('Failed to start MediaRecorder', error);
      cameraState.recorder = null;
      cameraState.recorderMimeType = '';
      showCameraStatus(error.message || 'Video opnemen mislukt.', 'error');
      updateCameraButtons(Boolean(cameraState.stream));
    }
  }

  function stopVideoRecording(cancel = false) {
    if (!cameraState.recorder) {
      return;
    }

    cameraState.recordingCancelled = cancel;
    try {
      if (cameraState.recorder.state !== 'inactive') {
        cameraState.recorder.stop();
      }
    } catch (error) {
      console.error('Failed to stop recorder', error);
    }
    if (videoStopButton) {
      videoStopButton.disabled = true;
    }
    updateCameraButtons(Boolean(cameraState.stream));
  }

  async function saveVideo() {
    if (!cameraState.videoBlob) {
      showCameraStatus('Maak eerst een video-opname voordat je opslaat.', 'warning');
      return;
    }

    if (videoSaveButton) {
      videoSaveButton.disabled = true;
      videoSaveButton.textContent = 'Opslaan…';
    }

    try {
      const base64 = await blobToBase64(cameraState.videoBlob);
      const mimeType = cameraState.videoBlob.type || 'video/webm';
      const extension = getExtensionFromMime(mimeType) || 'webm';
      const payload = {
        object_type: 'file',
        object_name: `memo-video-${formatTimestampForName()}.${extension}`,
        object_data: base64,
        file_size: cameraState.videoBlob.size,
        mime_type: mimeType,
        note: `Video gemaakt via memo-camera op ${new Date().toLocaleString('nl-NL')}`
      };
      await saveSharedObject(payload);
    } catch (error) {
      if (error && error.message) {
        showCameraStatus(error.message, 'error');
      }
    } finally {
      if (videoSaveButton) {
        videoSaveButton.disabled = !cameraState.videoBlob;
        videoSaveButton.textContent = 'Object opslaan';
      }
    }
  }

  async function saveSharedObject(payload) {
    const finalPayload = Object.assign({}, payload);
    if (!finalPayload.note) {
      finalPayload.note = `Opgeslagen via memo-camera op ${new Date().toLocaleString('nl-NL')}`;
    }

    try {
      const response = await fetch('/api/shared', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'same-origin',
        body: JSON.stringify(finalPayload)
      });

      const contentType = response.headers.get('content-type') || '';
      let data = {};
      if (contentType.includes('application/json')) {
        data = await response.json().catch(() => ({}));
      }

      if (!response.ok || data.status !== 'ok') {
        const detail = data && (data.detail || data.message);
        throw new Error(detail || `${response.status} ${response.statusText}`);
      }

      showCameraStatus('Object opgeslagen bij gedeelde items.', 'success');
      return data;
    } catch (error) {
      console.error('Failed to save shared object', error);
      showCameraStatus(error.message || 'Opslaan mislukt.', 'error');
      throw error;
    }
  }

  function setupCameraControls() {
    if (!cameraSection) {
      return;
    }

    updateCameraButtons(Boolean(cameraState.stream));

    const hasMediaDevices = navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function';
    if (!hasMediaDevices) {
      if (cameraStartButton) {
        cameraStartButton.disabled = true;
        cameraStartButton.textContent = 'Camera niet beschikbaar';
      }
      updateCameraButtons(false);
      showCameraStatus('Camera wordt niet ondersteund in deze browser.', 'error');
      return;
    }

    if (cameraStartButton) {
      cameraStartButton.addEventListener('click', async () => {
        cameraStartButton.disabled = true;
        try {
          await ensureCameraStream();
        } finally {
          updateCameraButtons(Boolean(cameraState.stream));
        }
      });
    }

    if (cameraStopButton) {
      cameraStopButton.addEventListener('click', () => {
        stopCameraStream();
      });
    }

    if (photoCaptureButton) {
      photoCaptureButton.addEventListener('click', capturePhoto);
    }

    if (photoSaveButton) {
      photoSaveButton.addEventListener('click', savePhoto);
    }

    if (qrToggleButton) {
      if (supportsBarcodeDetector) {
        qrToggleButton.addEventListener('click', async () => {
          if (cameraState.qrActive) {
            stopQrScan({ keepResult: true });
            showCameraStatus('QR-scanner gestopt.', 'info');
            updateCameraButtons(Boolean(cameraState.stream));
            return;
          }

          qrToggleButton.disabled = true;
          try {
            await startQrScan();
          } finally {
            updateCameraButtons(Boolean(cameraState.stream));
          }
        });
      } else {
        qrToggleButton.disabled = true;
        qrToggleButton.textContent = 'QR-scanner niet ondersteund';
      }
    }

    if (qrSaveButton) {
      qrSaveButton.addEventListener('click', saveQrResult);
    }

    if (videoRecordButton) {
      if (supportsMediaRecorder) {
        videoRecordButton.addEventListener('click', startVideoRecording);
      } else {
        videoRecordButton.disabled = true;
        videoRecordButton.textContent = 'Video niet ondersteund';
      }
    }

    if (videoStopButton) {
      videoStopButton.addEventListener('click', () => stopVideoRecording(false));
    }

    if (videoSaveButton) {
      videoSaveButton.addEventListener('click', saveVideo);
    }

    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        if (cameraState.recorder && cameraState.recorder.state === 'recording') {
          stopVideoRecording(true);
        }
        if (cameraState.stream) {
          stopCameraStream();
        }
      }
    });

    window.addEventListener('pagehide', () => {
      if (cameraState.stream) {
        stopCameraStream();
      }
    });

    showCameraStatus('Start de camera om deze functies te gebruiken.', 'info');
    updateCameraButtons(false);
  }

  function showTranscriptionStatus(message, type = 'info') {
    if (!transcriptionStatusEl) {
      return;
    }

    transcriptionStatusEl.textContent = message;
    transcriptionStatusEl.style.display = 'block';
    transcriptionStatusEl.classList.remove('status-success', 'status-error', 'status-warning');

    const className = type === 'success'
      ? 'status-success'
      : type === 'error'
        ? 'status-error'
        : type === 'warning'
          ? 'status-warning'
          : '';

    if (className) {
      transcriptionStatusEl.classList.add(className);
    }

    if (transcriptionStatusTimeoutId) {
      window.clearTimeout(transcriptionStatusTimeoutId);
    }

    transcriptionStatusTimeoutId = window.setTimeout(() => {
      transcriptionStatusEl.style.display = 'none';
      transcriptionStatusEl.classList.remove('status-success', 'status-error', 'status-warning');
      transcriptionStatusTimeoutId = null;
    }, 7000);
  }

  function clearTranscriptionFeedback() {
    if (transcriptionStatusTimeoutId) {
      window.clearTimeout(transcriptionStatusTimeoutId);
      transcriptionStatusTimeoutId = null;
    }
    if (transcriptionStatusEl) {
      transcriptionStatusEl.textContent = '';
      transcriptionStatusEl.style.display = 'none';
      transcriptionStatusEl.classList.remove('status-success', 'status-error', 'status-warning');
    }
    if (transcriptionResultEl) {
      transcriptionResultEl.classList.remove('is-visible');
      transcriptionResultEl.innerHTML = '';
    }
  }

  function formatTranscriptionTime(value) {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      return null;
    }
    const totalSeconds = Math.max(0, value);
    const minutes = Math.floor(totalSeconds / 60);
    const secondsFloat = totalSeconds - (minutes * 60);
    const seconds = Math.floor(secondsFloat);
    const remainder = secondsFloat - seconds;
    let formatted = `${minutes}:${String(seconds).padStart(2, '0')}`;
    if (remainder > 0.05) {
      const decimals = Math.round(remainder * 10);
      formatted += `.${String(decimals).padStart(1, '0')}`;
    }
    return formatted;
  }

  function renderTranscriptionResult(segments, fallbackText) {
    if (!transcriptionResultEl) {
      return;
    }

    transcriptionResultEl.innerHTML = '';

    const items = Array.isArray(segments) ? segments : [];
    if (items.length) {
      items.forEach((segment) => {
        if (!segment || typeof segment.text !== 'string' || !segment.text.trim()) {
          return;
        }
        const wrapper = document.createElement('div');
        wrapper.className = 'memo-transcription-segment';

        const speaker = document.createElement('span');
        speaker.className = 'memo-transcription-speaker';
        speaker.textContent = segment.speaker || 'Spreker';

        const timeParts = [];
        if (typeof segment.start === 'number') {
          const startText = formatTranscriptionTime(segment.start);
          if (startText) {
            timeParts.push(startText);
          }
        }
        if (typeof segment.end === 'number') {
          const endText = formatTranscriptionTime(segment.end);
          if (endText) {
            if (timeParts.length) {
              timeParts.push(`– ${endText}`);
            } else {
              timeParts.push(endText);
            }
          }
        }
        if (timeParts.length) {
          const time = document.createElement('span');
          time.className = 'memo-transcription-time';
          time.textContent = timeParts.join(' ');
          speaker.appendChild(time);
        }

        const text = document.createElement('p');
        text.textContent = segment.text.trim();

        wrapper.appendChild(speaker);
        wrapper.appendChild(text);
        transcriptionResultEl.appendChild(wrapper);
      });
    }

    if (!transcriptionResultEl.childNodes.length) {
      const content = typeof fallbackText === 'string' && fallbackText.trim()
        ? fallbackText.trim()
        : 'Geen transcript beschikbaar.';
      const paragraph = document.createElement('p');
      paragraph.textContent = content;
      transcriptionResultEl.appendChild(paragraph);
    }

    transcriptionResultEl.classList.add('is-visible');
  }

  function renderMemos() {
    if (!memoListEl) {
      return;
    }

    memoListEl.innerHTML = '';

    if (!state.memos.length) {
      const emptyMessage = document.createElement('p');
      emptyMessage.className = 'memo-empty';
      emptyMessage.textContent = 'Nog geen memo\'s opgeslagen.';
      memoListEl.appendChild(emptyMessage);
      return;
    }

    const fragment = document.createDocumentFragment();

    state.memos.forEach((memo) => {
      fragment.appendChild(createMemoCard(memo));
    });

    memoListEl.appendChild(fragment);
  }

  function getSelectedTranscriptionFile() {
    if (!transcriptionFileInput || !transcriptionFileInput.files || !transcriptionFileInput.files.length) {
      return null;
    }
    return transcriptionFileInput.files[0];
  }

  async function handleTranscriptionSubmit(event) {
    event.preventDefault();
    if (!transcriptionForm || state.isTranscribing) {
      return;
    }

    const file = getSelectedTranscriptionFile();
    const urlValue = transcriptionUrlInput ? transcriptionUrlInput.value.trim() : '';

    if (!file && !urlValue) {
      showTranscriptionStatus('Upload een audio-/videobestand of vul een URL in.', 'warning');
      return;
    }

    const formData = new FormData();
    if (file) {
      formData.append('media', file);
    }
    if (urlValue) {
      formData.append('source_url', urlValue);
    }

    clearTranscriptionFeedback();
    showTranscriptionStatus('Transcriptie gestart…', 'info');
    state.isTranscribing = true;

    if (transcriptionSubmitButton) {
      transcriptionSubmitButton.disabled = true;
      transcriptionSubmitButton.textContent = 'Transcriberen…';
    }

    try {
      const response = await fetch('/api/memos/transcribe', {
        method: 'POST',
        body: formData
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.status !== 'ok') {
        const detail = data && (data.detail || data.message);
        throw new Error(detail || 'Transcriptie mislukt.');
      }

      if (!data.memo) {
        throw new Error('Ongeldig antwoord van de server.');
      }

      const newMemo = Object.assign({}, data.memo, { __highlight: true });
      state.memos.unshift(newMemo);
      renderMemos();

      const segments = Array.isArray(data.segments) ? data.segments : [];
      renderTranscriptionResult(segments, data.transcript || newMemo.content || '');

      const copied = await copyTextToClipboard(newMemo.content);
      if (copied) {
        showStatus('Transcriptie opgeslagen en gekopieerd naar klembord.', 'success');
      } else {
        showStatus('Transcriptie opgeslagen als memo.', 'success');
      }
      showTranscriptionStatus('Transcriptie voltooid en memo opgeslagen.', 'success');

      if (transcriptionForm) {
        transcriptionForm.reset();
      }
      if (transcriptionFileInput) {
        transcriptionFileInput.value = '';
      }
    } catch (error) {
      console.error('Transcriptie van memo mislukt', error);
      showTranscriptionStatus(error.message || 'Transcriptie mislukt.', 'error');
      showStatus(error.message || 'Transcriptie mislukt.', 'error');
    } finally {
      state.isTranscribing = false;
      if (transcriptionSubmitButton) {
        transcriptionSubmitButton.disabled = false;
        transcriptionSubmitButton.textContent = 'Transcriberen';
      }
    }
  }

  function setupTranscriptionUpload() {
    if (!transcriptionForm) {
      return;
    }
    transcriptionForm.addEventListener('submit', handleTranscriptionSubmit);
  }

  function createMemoCard(memo) {
    const card = document.createElement('article');
    card.className = 'memo-card';
    card.dataset.memoId = String(memo.id);

    if (memo.__highlight) {
      card.classList.add('memo-card--highlight');
      window.setTimeout(() => {
        card.classList.remove('memo-card--highlight');
        delete memo.__highlight;
      }, 1600);
    }

    const header = document.createElement('div');
    header.className = 'memo-card__header';

    const timestamps = document.createElement('div');
    timestamps.className = 'memo-card__timestamps';

    const created = document.createElement('span');
    created.className = 'memo-card__timestamp';
    created.textContent = `Aangemaakt: ${formatMemoTime(memo.created_at)}`;
    timestamps.appendChild(created);

    if (memo.updated_at && memo.updated_at !== memo.created_at) {
      const updated = document.createElement('span');
      updated.className = 'memo-card__timestamp memo-card__timestamp--updated';
      updated.textContent = `Bijgewerkt: ${formatMemoTime(memo.updated_at)}`;
      timestamps.appendChild(updated);
    }

    const actions = document.createElement('div');
    actions.className = 'memo-card__actions';

    const copyButton = document.createElement('button');
    copyButton.type = 'button';
    copyButton.className = 'memo-copy-btn focus-ring';
    copyButton.textContent = '📋 Kopiëren';
    actions.appendChild(copyButton);

    const editButton = document.createElement('button');
    editButton.type = 'button';
    editButton.className = 'memo-edit-btn focus-ring';
    editButton.textContent = '✏️ Bewerken';
    actions.appendChild(editButton);

    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.className = 'memo-delete-btn focus-ring';
    deleteButton.textContent = '🗑️ Verwijderen';
    actions.appendChild(deleteButton);

    header.appendChild(timestamps);
    header.appendChild(actions);

    const content = document.createElement('p');
    content.className = 'memo-card__content';
    content.textContent = memo.content;

    const editArea = document.createElement('div');
    editArea.className = 'memo-edit-area';

    const label = document.createElement('label');
    label.className = 'sr-only';
    label.setAttribute('for', `memo-edit-${memo.id}`);
    label.textContent = 'Bewerk memo';

    const textarea = document.createElement('textarea');
    textarea.id = `memo-edit-${memo.id}`;
    textarea.rows = 4;
    textarea.value = memo.content;

    const editActions = document.createElement('div');
    editActions.className = 'memo-edit-actions';

    const saveButton = document.createElement('button');
    saveButton.type = 'button';
    saveButton.className = 'memo-save-btn focus-ring';
    saveButton.textContent = 'Opslaan';

    const cancelButton = document.createElement('button');
    cancelButton.type = 'button';
    cancelButton.className = 'memo-cancel-btn focus-ring';
    cancelButton.textContent = 'Annuleren';

    editActions.appendChild(saveButton);
    editActions.appendChild(cancelButton);

    editArea.appendChild(label);
    editArea.appendChild(textarea);
    editArea.appendChild(editActions);

    card.appendChild(header);
    card.appendChild(content);
    card.appendChild(editArea);

    editButton.addEventListener('click', () => {
      const isEditing = card.classList.toggle('is-editing');
      if (isEditing) {
        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
      } else {
        textarea.value = memo.content;
      }
    });

    copyButton.addEventListener('click', async () => {
      const originalText = copyButton.textContent;
      if (!memo.content) {
        showStatus('Deze memo is leeg en kan niet gekopieerd worden.', 'warning');
        return;
      }

      copyButton.disabled = true;
      copyButton.textContent = 'Kopiëren…';

      const success = await copyTextToClipboard(memo.content);

      copyButton.disabled = false;
      copyButton.textContent = originalText;

      if (success) {
        showStatus('Memo gekopieerd naar klembord.', 'success');
      } else {
        showStatus('Kopiëren naar klembord mislukt.', 'error');
      }
    });

    cancelButton.addEventListener('click', () => {
      card.classList.remove('is-editing');
      textarea.value = memo.content;
    });

    saveButton.addEventListener('click', async () => {
      const updatedContent = textarea.value.trim();
      if (!updatedContent) {
        showStatus('Memo mag niet leeg zijn.', 'warning');
        textarea.focus();
        return;
      }

      saveButton.disabled = true;
      saveButton.textContent = 'Opslaan…';

      try {
        const response = await fetch(`/api/memos/${memo.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ content: updatedContent })
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.status !== 'ok') {
          const detail = data && (data.detail || data.message);
          throw new Error(detail || 'Onbekende fout bij het bijwerken van de memo.');
        }

        const updatedMemo = data.memo;
        if (!updatedMemo) {
          throw new Error('Ongeldig antwoord van de server.');
        }

        Object.assign(memo, updatedMemo, { __highlight: true });
        card.classList.remove('is-editing');
        renderMemos();
        showStatus('Memo bijgewerkt.', 'success');
      } catch (error) {
        console.error('Failed to update memo', error);
        showStatus(error.message || 'Bijwerken mislukt.', 'error');
      } finally {
        saveButton.disabled = false;
        saveButton.textContent = 'Opslaan';
      }
    });

    deleteButton.addEventListener('click', async () => {
      const confirmed = window.confirm('Weet je zeker dat je deze memo wilt archiveren?');
      if (!confirmed) {
        return;
      }

      const originalText = deleteButton.textContent;
      deleteButton.disabled = true;
      deleteButton.textContent = 'Verwijderen…';

      try {
        const response = await fetch(`/api/memos/${memo.id}`, {
          method: 'DELETE'
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.status !== 'ok') {
          const detail = data && (data.detail || data.message);
          throw new Error(detail || 'Onbekende fout bij het archiveren van de memo.');
        }

        state.memos = state.memos.filter((existing) => existing.id !== memo.id);
        renderMemos();
        showStatus('Memo verplaatst naar archief.', 'success');
      } catch (error) {
        console.error('Failed to archive memo', error);
        showStatus(error.message || 'Archiveren mislukt.', 'error');
      } finally {
        deleteButton.disabled = false;
        deleteButton.textContent = originalText;
      }
    });

    return card;
  }

  async function loadMemos() {
    try {
      const response = await fetch('/api/memos');
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.status !== 'ok') {
        const detail = data && (data.detail || data.message);
        throw new Error(detail || 'Memo\'s konden niet geladen worden.');
      }

      const memos = Array.isArray(data.memos) ? data.memos : [];
      state.memos = memos;
      renderMemos();
    } catch (error) {
      console.error('Failed to load memos', error);
      showStatus(error.message || 'Memo\'s konden niet geladen worden.', 'error');
      state.memos = [];
      renderMemos();
    }
  }

  async function saveMemo(content) {
    try {
      const response = await fetch('/api/memos', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content })
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.status !== 'ok') {
        const detail = data && (data.detail || data.message);
        throw new Error(detail || 'Memo kon niet opgeslagen worden.');
      }

      if (!data.memo) {
        throw new Error('Ongeldig antwoord van de server.');
      }

      const newMemo = Object.assign({}, data.memo, { __highlight: true });
      state.memos.unshift(newMemo);
      renderMemos();

      const copySucceeded = await copyTextToClipboard(newMemo.content);
      if (copySucceeded) {
        showStatus('Memo opgeslagen en gekopieerd naar klembord.', 'success');
      } else {
        showStatus('Memo opgeslagen, maar kopiëren naar klembord is mislukt.', 'warning');
      }
      return true;
    } catch (error) {
      console.error('Failed to save memo', error);
      showStatus(error.message || 'Opslaan mislukt.', 'error');
      return false;
    }
  }

  async function handleManualSave() {
    const value = manualInput.value.trim();
    if (!value) {
      showStatus('Vul eerst een memo in.', 'warning');
      manualInput.focus();
      return;
    }

    manualSaveButton.disabled = true;
    manualSaveButton.textContent = 'Opslaan…';

    const success = await saveMemo(value);
    if (success) {
      manualInput.value = '';
      manualInput.focus();
    }

    manualSaveButton.disabled = false;
    manualSaveButton.textContent = 'Memo opslaan';
  }

  function setupManualControls() {
    if (!manualSaveButton || !manualInput) {
      return;
    }

    manualSaveButton.addEventListener('click', handleManualSave);

    manualInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        handleManualSave();
      }
    });
  }

  function setupSpeechRecording() {
    if (!recordButton || !liveTranscriptEl) {
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      recordButton.disabled = true;
      recordButton.classList.add('memo-record-btn--disabled');
      recordButton.textContent = 'Spraakopname niet beschikbaar';
      showStatus('Spraakherkenning wordt niet door deze browser ondersteund. Gebruik het tekstveld om memo\'s te maken.', 'warning');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'nl-NL';
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    let isRecording = false;
    let recognitionHadError = false;
    let transcriptParts = [];
    let interimTranscript = '';

    function resetRecordingUi() {
      isRecording = false;
      recordButton.classList.remove('memo-record-btn--recording');
      recordButton.textContent = '🎙️ Houd ingedrukt om op te nemen';
      liveTranscriptEl.textContent = '';
      transcriptParts = [];
      interimTranscript = '';
    }

    function startRecording() {
      if (isRecording) {
        return;
      }

      recognitionHadError = false;
      transcriptParts = [];
      interimTranscript = '';

      try {
        recognition.start();
      } catch (error) {
        console.error('Failed to start speech recognition', error);
        showStatus('Kon de spraakopname niet starten.', 'error');
      }
    }

    function stopRecording() {
      if (!isRecording) {
        return;
      }
      recognition.stop();
    }

    recognition.addEventListener('start', () => {
      isRecording = true;
      recordButton.classList.add('memo-record-btn--recording');
      recordButton.textContent = '🎙️ Opnemen… laat los om te bewaren';
      liveTranscriptEl.textContent = 'Luisteren…';
    });

    recognition.addEventListener('result', (event) => {
      interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const transcript = result[0] && result[0].transcript ? result[0].transcript.trim() : '';
        if (!transcript) {
          continue;
        }
        if (result.isFinal) {
          transcriptParts.push(transcript);
        } else {
          interimTranscript += `${transcript} `;
        }
      }
      const combined = [...transcriptParts, interimTranscript.trim()].filter(Boolean).join(' ');
      liveTranscriptEl.textContent = combined || 'Luisteren…';
    });

    recognition.addEventListener('error', (event) => {
      recognitionHadError = true;
      console.error('Speech recognition error', event);
      if (event.error === 'no-speech') {
        showStatus('Geen spraak gedetecteerd. Probeer het opnieuw.', 'warning');
      } else if (event.error === 'not-allowed') {
        showStatus('Toegang tot de microfoon geweigerd.', 'error');
      } else {
        showStatus(`Opnamefout: ${event.error}`, 'error');
      }
      resetRecordingUi();
    });

    recognition.addEventListener('end', () => {
      const finalTranscript = (transcriptParts.join(' ').trim() || interimTranscript.trim());
      const hadError = recognitionHadError;
      resetRecordingUi();
      if (hadError) {
        return;
      }
      if (finalTranscript) {
        saveMemo(finalTranscript);
      } else {
        showStatus('Geen tekst herkend. Probeer het opnieuw.', 'warning');
      }
    });

    const startHandler = (event) => {
      if (event.type === 'mousedown' && event.button !== 0) {
        return;
      }
      event.preventDefault();
      startRecording();
    };

    const stopHandler = (event) => {
      event.preventDefault();
      stopRecording();
    };

    recordButton.addEventListener('mousedown', startHandler);
    recordButton.addEventListener('touchstart', startHandler, { passive: false });

    recordButton.addEventListener('mouseup', stopHandler);
    recordButton.addEventListener('mouseleave', stopHandler);
    recordButton.addEventListener('touchend', stopHandler, { passive: false });
    recordButton.addEventListener('touchcancel', stopHandler, { passive: false });

    recordButton.addEventListener('click', (event) => {
      event.preventDefault();
    });
  }

  function init() {
    setupManualControls();
    setupTranscriptionUpload();
    setupSpeechRecording();
    setupCameraControls();
    loadMemos();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
