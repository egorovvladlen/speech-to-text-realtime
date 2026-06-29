from __future__ import annotations

from dataclasses import dataclass
import io
import os
from typing import Iterable

from .config import AppConfig
from .rag import KnowledgeChunk


@dataclass(frozen=True)
class Suggestion:
    mode: str
    text: str


class AIClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        if config.stt_provider != "openai" or config.text_provider != "openai":
            raise RuntimeError("Only OpenAI providers are implemented in this MVP.")
        if not config.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is empty in .env.")

        from openai import OpenAI

        kwargs = {"api_key": config.openai_api_key}
        if config.openai_base_url:
            kwargs["base_url"] = config.openai_base_url
        elif not os.getenv("OPENAI_BASE_URL", "").strip():
            os.environ.pop("OPENAI_BASE_URL", None)
        self.client = OpenAI(**kwargs)

    def transcribe(self, wav_bytes: bytes) -> str:
        audio_file = io.BytesIO(wav_bytes)
        audio_file.name = "speaker-chunk.wav"
        kwargs = {"model": self.config.stt_model, "file": audio_file}
        if self.config.stt_language:
            kwargs["language"] = self.config.stt_language
        if self.config.stt_prompt:
            kwargs["prompt"] = self.config.stt_prompt
        response = self.client.audio.transcriptions.create(**kwargs)
        return (getattr(response, "text", "") or "").strip()

    def translate(self, text: str) -> str:
        if not self.config.enable_translation:
            return text
        system = (
            "You are a realtime call translator. Return only the translated text, "
            "without explanations or quotes."
        )
        source = self.config.source_language if self.config.stt_language else "the detected source language"
        user = f"Translate from {source} to {self.config.target_language}:\n\n{text}"
        return self._complete(system=system, user=user).strip()

    def rag_suggestions(
        self,
        original: str,
        translated: str,
        chunks: Iterable[KnowledgeChunk],
        suggestions_language: str,
    ) -> list[Suggestion]:
        context_parts = []
        for chunk in chunks:
            context_parts.append(f"[{chunk.source}]\n{chunk.text}")
        if not context_parts:
            return []

        system = (
            "You help a support/sales/operator employee during a live conversation. "
            "Use only the provided company knowledge. "
            f"Return 1-3 concise answer suggestions in {suggestions_language}."
        )
        user = (
            "Conversation fragment:\n"
            f"Original: {original}\n"
            f"Translation: {translated}\n\n"
            "Company knowledge:\n"
            + "\n\n---\n\n".join(context_parts)
        )
        return [Suggestion(mode="rag", text=item) for item in self._lines(self._complete(system, user))]

    def general_advice(self, original: str, translated: str, suggestions_language: str) -> list[Suggestion]:
        system = (
            "You are a live conversation coach. Return 1-3 short, practical suggestions "
            f"for what the user can answer next in {suggestions_language}. Avoid generic encouragement."
        )
        user = f"Original: {original}\nTranslation: {translated}"
        return [Suggestion(mode="general", text=item) for item in self._lines(self._complete(system, user))]

    def _complete(self, system: str, user: str) -> str:
        if self.config.openai_text_api == "responses" and hasattr(self.client, "responses"):
            response = self.client.responses.create(
                model=self.config.text_model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            output_text = getattr(response, "output_text", "")
            if output_text:
                return output_text

        response = self.client.chat.completions.create(
            model=self.config.text_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def _lines(text: str) -> list[str]:
        lines = []
        for line in text.splitlines():
            item = line.strip(" \t-*0123456789.").strip()
            if item:
                lines.append(item)
        if lines:
            return lines[:3]
        stripped = text.strip()
        return [stripped] if stripped else []
