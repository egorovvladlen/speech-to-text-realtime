from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import queue
import re
import threading
from typing import Any

from .ai import AIClient
from .audio import SpeakerLoopbackRecorder
from .config import AppConfig
from .rag import KnowledgeBase


@dataclass(frozen=True)
class StreamEvent:
    id: int
    created_at: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


class EventStore:
    def __init__(self, max_events: int) -> None:
        self.max_events = max_events
        self._events: list[StreamEvent] = []
        self._next_id = 1
        self._lock = threading.Lock()

    def add(self, kind: str, **payload: Any) -> StreamEvent:
        with self._lock:
            event = StreamEvent(
                id=self._next_id,
                created_at=datetime.now(timezone.utc).isoformat(),
                kind=kind,
                payload=payload,
            )
            self._next_id += 1
            self._events.append(event)
            if len(self._events) > self.max_events:
                self._events = self._events[-self.max_events :]
            return event

    def after(self, event_id: int) -> list[dict[str, Any]]:
        with self._lock:
            return [event.__dict__ for event in self._events if event.id > event_id]


class TranslationWorker:
    def __init__(self, config: AppConfig, events: EventStore) -> None:
        self.config = config
        self.events = events
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._running = False
        self._last_error = ""
        self._last_rms = 0.0
        self._transcript_log_path = ""
        self._suggestions_language = config.suggestions_language
        self._knowledge = KnowledgeBase(config.knowledge_base_path)

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return False
            self._stop.clear()
            self._running = True
            self._last_error = ""
            self._thread = threading.Thread(target=self._run, name="translation-worker", daemon=True)
            self._thread.start()
            return True

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        with self._lock:
            self._running = False

    def refresh_knowledge(self) -> int:
        self._knowledge.refresh()
        count = self._knowledge.count
        self.events.add("system", message=f"Knowledge base refreshed: {count} chunks.")
        return count

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "last_error": self._last_error,
                "last_rms": self._last_rms,
                "transcript_log_path": self._transcript_log_path,
                "suggestions_language": self._suggestions_language,
                "suggestions_language_label": self._suggestions_language_label_locked(),
                "knowledge_chunks": self._knowledge.count,
            }

    def set_suggestions_language(self, language: str) -> str:
        language = language.strip()
        if not language or len(language) > 40:
            raise ValueError("Invalid suggestions language.")
        with self._lock:
            self._suggestions_language = language
            label = self._suggestions_language_label_locked()
        self.events.add("system", message=f"Suggestions language: {label}")
        return language

    def _suggestions_language_label_locked(self) -> str:
        language = self._suggestions_language.strip()
        normalized = language.lower()
        if normalized in {"target", "translation", "translated"}:
            return self.config.target_language
        if normalized in {"source", "original"}:
            if self.config.source_language.lower() in {"", "auto", "detect"}:
                return "the original conversation language"
            return self.config.source_language
        return language

    def _suggestions_language_label(self) -> str:
        with self._lock:
            return self._suggestions_language_label_locked()

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._last_error = message
        self.events.add("error", message=message)

    def _set_rms(self, rms: float) -> None:
        with self._lock:
            self._last_rms = rms

    def _create_transcript_log(self) -> Path | None:
        if not self.config.enable_transcript_log:
            with self._lock:
                self._transcript_log_path = ""
            return None

        self.config.transcript_log_dir.mkdir(parents=True, exist_ok=True)
        started_at = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = self.config.transcript_log_dir / f"transcript-{started_at}.md"
        header = (
            f"# Transcript {started_at}\n\n"
            f"- Source language: {self.config.source_language}\n"
            f"- Target language: {self.config.target_language}\n"
            f"- Speaker: {self.config.speaker_name or 'default speaker'}\n\n"
        )
        path.write_text(header, encoding="utf-8")
        with self._lock:
            self._transcript_log_path = str(path)
        return path

    @staticmethod
    def _append_transcript_log(path: Path | None, original: str, translated: str) -> None:
        if not path:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = (
            f"## {timestamp}\n\n"
            f"**Original**\n\n{original}\n\n"
            f"**Translation**\n\n{translated}\n\n"
        )
        with path.open("a", encoding="utf-8") as log_file:
            log_file.write(entry)

    @staticmethod
    def _trim_repeated_overlap(previous: str, current: str, max_words: int = 10) -> str:
        prev_words = re.findall(r"\S+", previous.strip())
        current_words = re.findall(r"\S+", current.strip())
        if not prev_words or not current_words:
            return current.strip()

        for size in range(min(max_words, len(prev_words), len(current_words)), 0, -1):
            prev_tail = " ".join(prev_words[-size:]).casefold()
            current_head = " ".join(current_words[:size]).casefold()
            if prev_tail == current_head:
                if size == len(current_words) and size <= 2:
                    return current.strip()
                return " ".join(current_words[size:]).strip()
        return current.strip()

    def _run(self) -> None:
        last_text = ""
        transcript_log_path = self._create_transcript_log()
        audio_queue: queue.Queue[Any] = queue.Queue(maxsize=self.config.audio_queue_max_chunks)
        dropped_chunks = 0

        def capture_loop() -> None:
            nonlocal dropped_chunks
            try:
                recorder = SpeakerLoopbackRecorder(self.config)
                for chunk in recorder.stream(self._stop):
                    if self._stop.is_set():
                        break
                    self._set_rms(chunk.rms)
                    if chunk.rms < self.config.silence_rms_threshold:
                        continue
                    try:
                        audio_queue.put_nowait(chunk)
                    except queue.Full:
                        try:
                            audio_queue.get_nowait()
                        except queue.Empty:
                            pass
                        audio_queue.put_nowait(chunk)
                        dropped_chunks += 1
                        if dropped_chunks == 1 or dropped_chunks % 10 == 0:
                            self.events.add(
                                "system",
                                message=f"Dropped {dropped_chunks} old audio chunk(s) to keep realtime.",
                            )
            except Exception as exc:
                self._set_error(str(exc))
            finally:
                try:
                    audio_queue.put_nowait(None)
                except queue.Full:
                    try:
                        audio_queue.get_nowait()
                    except queue.Empty:
                        pass
                    audio_queue.put_nowait(None)

        try:
            ai = AIClient(self.config)
            capture_thread = threading.Thread(target=capture_loop, name="audio-capture", daemon=True)
            capture_thread.start()
            self.events.add("system", message="Listening to speaker loopback.")
            if transcript_log_path:
                self.events.add("system", message=f"Transcript log: {transcript_log_path}")

            while not self._stop.is_set():
                try:
                    chunk = audio_queue.get(timeout=0.2)
                except queue.Empty:
                    if not capture_thread.is_alive():
                        break
                    continue
                if chunk is None:
                    break
                if self._stop.is_set():
                    break

                original = ai.transcribe(chunk.wav_bytes)
                original = self._trim_repeated_overlap(last_text, original)
                if not original:
                    continue
                last_text = original

                translated = ai.translate(original)
                self._append_transcript_log(transcript_log_path, original, translated)
                suggestions = []
                suggestions_language = self._suggestions_language_label()
                if self.config.enable_rag_suggestions:
                    matches = self._knowledge.search(f"{original}\n{translated}", self.config.rag_max_chunks)
                    suggestions.extend(
                        item.__dict__
                        for item in ai.rag_suggestions(original, translated, matches, suggestions_language)
                    )
                if self.config.enable_general_advice:
                    suggestions.extend(item.__dict__ for item in ai.general_advice(original, translated, suggestions_language))

                self.events.add(
                    "utterance",
                    original=original,
                    translated=translated,
                    suggestions=suggestions,
                    rms=chunk.rms,
                )
        except Exception as exc:
            self._set_error(str(exc))
        finally:
            with self._lock:
                self._running = False
            self.events.add("system", message="Listener stopped.")
