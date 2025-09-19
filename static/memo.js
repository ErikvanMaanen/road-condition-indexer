(function () {
  'use strict';

  const state = {
    memos: []
  };

  const recordButton = document.getElementById('memo-record-btn');
  const liveTranscriptEl = document.getElementById('memo-live-transcript');
  const manualInput = document.getElementById('memo-manual-input');
  const manualSaveButton = document.getElementById('memo-manual-save');
  const statusEl = document.getElementById('memo-status');
  const memoListEl = document.getElementById('memo-list');

  let statusTimeoutId = null;

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

    const editButton = document.createElement('button');
    editButton.type = 'button';
    editButton.className = 'memo-edit-btn focus-ring';
    editButton.textContent = '✏️ Bewerken';
    actions.appendChild(editButton);

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
      showStatus('Memo opgeslagen.', 'success');
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
    setupSpeechRecording();
    loadMemos();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
