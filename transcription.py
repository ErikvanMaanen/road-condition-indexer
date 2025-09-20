"""Utilities for transcribing audio and video content with speaker diarization."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Generator, Optional

import requests


class TranscriptionServiceError(RuntimeError):
    """Base exception for transcription failures."""


class TranscriptionConfigError(TranscriptionServiceError):
    """Raised when the transcription service is misconfigured."""


class TranscriptionFailedError(TranscriptionServiceError):
    """Raised when the remote transcription service returns an error."""


class TranscriptionService:
    """High level helper for AssemblyAI-based transcriptions."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.assemblyai.com/v2",
        poll_interval: float = 3.0,
        max_wait_seconds: float = 600.0,
    ) -> None:
        self.api_key = api_key or os.getenv("ASSEMBLYAI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.max_wait_seconds = max_wait_seconds

    @property
    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise TranscriptionConfigError("AssemblyAI API-sleutel ontbreekt")
        return {"authorization": self.api_key}

    def transcribe(
        self,
        *,
        file_path: Optional[Path] = None,
        source_url: Optional[str] = None,
    ) -> Dict[str, object]:
        """Transcribe the provided media and return the raw API payload."""

        if not file_path and not source_url:
            raise ValueError("Bestand of URL vereist voor transcriptie")

        headers = self._headers

        if file_path is not None:
            audio_url = self._upload_file(file_path, headers)
        else:
            audio_url = source_url

        assert audio_url is not None

        transcript_id = self._create_transcript(audio_url, headers)
        return self._poll_transcript(transcript_id, headers)

    def _upload_file(self, file_path: Path, headers: Dict[str, str]) -> str:
        if not file_path.exists():
            raise FileNotFoundError(f"Bestand niet gevonden: {file_path}")

        upload_url = f"{self.base_url}/upload"
        with file_path.open("rb") as stream:
            response = requests.post(upload_url, headers=headers, data=self._read_file(stream))
        response.raise_for_status()
        payload = response.json()
        audio_url = payload.get("upload_url")
        if not audio_url:
            raise TranscriptionFailedError("Upload mislukt: geen upload_url ontvangen")
        return audio_url

    def _create_transcript(self, audio_url: str, headers: Dict[str, str]) -> str:
        create_url = f"{self.base_url}/transcript"
        body = {"audio_url": audio_url, "speaker_labels": True}
        response = requests.post(create_url, json=body, headers=headers)
        response.raise_for_status()
        payload = response.json()
        transcript_id = payload.get("id")
        if not transcript_id:
            raise TranscriptionFailedError("Transcriptie-aanvraag gaf geen ID terug")
        return transcript_id

    def _poll_transcript(self, transcript_id: str, headers: Dict[str, str]) -> Dict[str, object]:
        status_url = f"{self.base_url}/transcript/{transcript_id}"
        deadline = time.monotonic() + self.max_wait_seconds
        while True:
            response = requests.get(status_url, headers=headers)
            response.raise_for_status()
            payload = response.json()
            status = payload.get("status")
            if status == "completed":
                return payload
            if status == "error":
                error_message = payload.get("error") or "Transcriptie mislukt"
                raise TranscriptionFailedError(error_message)
            if time.monotonic() > deadline:
                raise TranscriptionFailedError("Transcriptie duurde te lang")
            time.sleep(self.poll_interval)

    @staticmethod
    def _read_file(stream) -> Generator[bytes, None, None]:
        chunk_size = 5 * 1024 * 1024
        while True:
            data = stream.read(chunk_size)
            if not data:
                break
            yield data
