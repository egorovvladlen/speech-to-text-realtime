from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    return int(value)


def _float(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    return float(value)


@dataclass(frozen=True)
class AppConfig:
    root: Path
    openai_api_key: str
    openai_base_url: str
    source_language: str
    target_language: str
    speaker_name: str
    sample_rate: int
    chunk_seconds: float
    audio_overlap_seconds: float
    silence_rms_threshold: float
    stt_provider: str
    stt_model: str
    stt_prompt: str
    text_provider: str
    text_model: str
    openai_text_api: str
    enable_translation: bool
    enable_rag_suggestions: bool
    enable_general_advice: bool
    knowledge_base_path: Path
    rag_max_chunks: int
    suggestions_language: str
    enable_transcript_log: bool
    transcript_log_dir: Path
    app_host: str
    app_port: int
    auto_start: bool
    pid_file: Path
    audio_queue_max_chunks: int
    max_events: int = 250

    @classmethod
    def from_env(cls, root: Path | None = None) -> "AppConfig":
        root = (root or Path.cwd()).resolve()
        load_dotenv(root / ".env", override=False)

        knowledge_path = Path(os.getenv("KNOWLEDGE_BASE_PATH", "knowledge_base"))
        if not knowledge_path.is_absolute():
            knowledge_path = root / knowledge_path

        transcript_log_dir = Path(os.getenv("TRANSCRIPT_LOG_DIR", "logs/transcripts"))
        if not transcript_log_dir.is_absolute():
            transcript_log_dir = root / transcript_log_dir

        return cls(
            root=root,
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "").strip(),
            source_language=os.getenv("SOURCE_LANGUAGE", "auto").strip() or "auto",
            target_language=os.getenv("TARGET_LANGUAGE", "ru").strip() or "ru",
            speaker_name=os.getenv("SPEAKER_NAME", "").strip(),
            sample_rate=_int("SAMPLE_RATE", 16000),
            chunk_seconds=_float("CHUNK_SECONDS", 2.0),
            audio_overlap_seconds=_float("AUDIO_OVERLAP_SECONDS", 0.6),
            silence_rms_threshold=_float("SILENCE_RMS_THRESHOLD", 0.004),
            stt_provider=os.getenv("STT_PROVIDER", "openai").strip().lower(),
            stt_model=os.getenv("STT_MODEL", "gpt-4o-transcribe").strip(),
            stt_prompt=os.getenv("STT_PROMPT", "").strip(),
            text_provider=os.getenv("TEXT_PROVIDER", "openai").strip().lower(),
            text_model=os.getenv("TEXT_MODEL", "gpt-4o-mini").strip(),
            openai_text_api=os.getenv("OPENAI_TEXT_API", "chat").strip().lower(),
            enable_translation=_bool("ENABLE_TRANSLATION", True),
            enable_rag_suggestions=_bool("ENABLE_RAG_SUGGESTIONS", False),
            enable_general_advice=_bool("ENABLE_GENERAL_ADVICE", False),
            knowledge_base_path=knowledge_path,
            rag_max_chunks=_int("RAG_MAX_CHUNKS", 4),
            suggestions_language=os.getenv("SUGGESTIONS_LANGUAGE", "target").strip() or "target",
            enable_transcript_log=_bool("ENABLE_TRANSCRIPT_LOG", True),
            transcript_log_dir=transcript_log_dir,
            app_host=os.getenv("APP_HOST", "127.0.0.1").strip(),
            app_port=_int("APP_PORT", 8787),
            auto_start=_bool("AUTO_START", False),
            pid_file=root / ".translator.pid",
            audio_queue_max_chunks=_int("AUDIO_QUEUE_MAX_CHUNKS", 3),
        )

    @property
    def stt_language(self) -> str | None:
        if self.source_language.lower() in {"", "auto", "detect"}:
            return None
        return self.source_language

    def public_settings(self) -> dict[str, object]:
        return {
            "source_language": self.source_language,
            "target_language": self.target_language,
            "speaker_name": self.speaker_name or "default speaker",
            "sample_rate": self.sample_rate,
            "chunk_seconds": self.chunk_seconds,
            "audio_overlap_seconds": self.audio_overlap_seconds,
            "stt_provider": self.stt_provider,
            "stt_model": self.stt_model,
            "stt_prompt": bool(self.stt_prompt),
            "text_provider": self.text_provider,
            "text_model": self.text_model,
            "translation": self.enable_translation,
            "rag_suggestions": self.enable_rag_suggestions,
            "general_advice": self.enable_general_advice,
            "suggestions_language": self.suggestions_language,
            "knowledge_base_path": str(self.knowledge_base_path),
            "transcript_log": self.enable_transcript_log,
            "transcript_log_dir": str(self.transcript_log_dir),
            "api_key_present": bool(self.openai_api_key),
            "base_url": self.openai_base_url or "default",
            "audio_queue_max_chunks": self.audio_queue_max_chunks,
        }
