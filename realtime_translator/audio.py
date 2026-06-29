from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import ctypes
import io
import os
import wave

import numpy as np

from .config import AppConfig


@dataclass(frozen=True)
class AudioChunk:
    wav_bytes: bytes
    rms: float
    sample_rate: int


def _import_soundcard():
    try:
        import soundcard as sc
    except ImportError as exc:
        raise RuntimeError("Install dependencies first: python -m pip install -r requirements.txt") from exc
    return sc


def _initialize_windows_com():
    if os.name != "nt":
        return lambda: None

    ole32 = ctypes.WinDLL("ole32")
    co_initialize_ex = ole32.CoInitializeEx
    co_initialize_ex.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    co_initialize_ex.restype = ctypes.c_long
    co_uninitialize = ole32.CoUninitialize
    co_uninitialize.argtypes = []
    co_uninitialize.restype = None

    coinit_multithreaded = 0x0
    rpc_e_changed_mode = -2147417850
    hr = co_initialize_ex(None, coinit_multithreaded)
    if hr in (0, 1):
        return co_uninitialize
    if hr == rpc_e_changed_mode:
        return lambda: None
    raise OSError(hr, f"CoInitializeEx failed: 0x{hr & 0xFFFFFFFF:08x}")


def audio_to_wav_bytes(samples: np.ndarray, sample_rate: int) -> tuple[bytes, float]:
    audio = np.asarray(samples, dtype=np.float32)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if audio.size == 0:
        return b"", 0.0

    rms = float(np.sqrt(np.mean(np.square(audio))))
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype(np.int16)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())
    return buffer.getvalue(), rms


def list_audio_devices() -> dict[str, list[dict[str, str]]]:
    sc = _import_soundcard()
    speakers = [
        {
            "name": getattr(speaker, "name", str(speaker)),
            "id": str(getattr(speaker, "id", "")),
        }
        for speaker in sc.all_speakers()
    ]
    microphones = [
        {
            "name": getattr(mic, "name", str(mic)),
            "id": str(getattr(mic, "id", "")),
        }
        for mic in sc.all_microphones(include_loopback=True)
    ]
    return {"speakers": speakers, "loopback_microphones": microphones}


class SpeakerLoopbackRecorder:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def _resolve_speaker(self):
        sc = _import_soundcard()
        speakers = list(sc.all_speakers())
        if not speakers:
            raise RuntimeError("No speaker output devices found.")

        wanted = self.config.speaker_name.strip().lower()
        if wanted:
            for speaker in speakers:
                name = getattr(speaker, "name", str(speaker)).lower()
                speaker_id = str(getattr(speaker, "id", "")).lower()
                if wanted in name or wanted in speaker_id:
                    return speaker
            available = ", ".join(getattr(s, "name", str(s)) for s in speakers)
            raise RuntimeError(f"SPEAKER_NAME not found: {self.config.speaker_name}. Available: {available}")

        return sc.default_speaker()

    def _loopback_microphone(self, speaker):
        sc = _import_soundcard()
        candidates = [getattr(speaker, "name", ""), getattr(speaker, "id", "")]
        for candidate in candidates:
            if not candidate:
                continue
            try:
                return sc.get_microphone(id=str(candidate), include_loopback=True)
            except Exception:
                pass

        speaker_name = getattr(speaker, "name", str(speaker)).lower()
        for mic in sc.all_microphones(include_loopback=True):
            mic_name = getattr(mic, "name", str(mic)).lower()
            if speaker_name and speaker_name in mic_name:
                return mic

        raise RuntimeError(f"Could not open loopback recorder for speaker: {getattr(speaker, 'name', speaker)}")

    def stream(self, stop_event) -> Iterable[AudioChunk]:
        _import_soundcard()
        uninitialize_com = _initialize_windows_com()
        try:
            speaker = self._resolve_speaker()
            loopback = self._loopback_microphone(speaker)
            frames = max(1, int(self.config.sample_rate * self.config.chunk_seconds))
            overlap_frames = max(0, int(self.config.sample_rate * self.config.audio_overlap_seconds))
            tail = np.empty((0,), dtype=np.float32)

            with loopback.recorder(samplerate=self.config.sample_rate) as recorder:
                while not stop_event.is_set():
                    samples = recorder.record(numframes=frames)
                    if overlap_frames:
                        audio = np.asarray(samples, dtype=np.float32)
                        if tail.size:
                            audio = np.concatenate([tail, audio], axis=0)
                        tail = np.asarray(samples, dtype=np.float32)[-overlap_frames:]
                    else:
                        audio = samples
                    wav_bytes, rms = audio_to_wav_bytes(audio, self.config.sample_rate)
                    if wav_bytes:
                        yield AudioChunk(wav_bytes=wav_bytes, rms=rms, sample_rate=self.config.sample_rate)
        finally:
            uninitialize_com()
