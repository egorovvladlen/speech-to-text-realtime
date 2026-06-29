from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


SUPPORTED_SUFFIXES = {".txt", ".md", ".json", ".csv"}


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    text: str
    score: int = 0


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[\wА-Яа-яЁё]{3,}", text)}


def _split_text(text: str, max_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        current = paragraph[:max_chars]
    if current:
        chunks.append(current)
    return chunks


class KnowledgeBase:
    def __init__(self, path: Path, chunk_chars: int = 1400) -> None:
        self.path = path
        self.chunk_chars = chunk_chars
        self._chunks: list[KnowledgeChunk] = []
        self.refresh()

    def refresh(self) -> None:
        chunks: list[KnowledgeChunk] = []
        if not self.path.exists():
            self._chunks = []
            return

        files = [p for p in self.path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES]
        for file_path in files:
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = file_path.read_text(encoding="cp1251", errors="ignore")
            rel = str(file_path.relative_to(self.path))
            for chunk in _split_text(text, self.chunk_chars):
                chunks.append(KnowledgeChunk(source=rel, text=chunk))
        self._chunks = chunks

    def search(self, query: str, limit: int) -> list[KnowledgeChunk]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        scored: list[KnowledgeChunk] = []
        for chunk in self._chunks:
            score = len(query_tokens & _tokens(chunk.text))
            if score:
                scored.append(KnowledgeChunk(source=chunk.source, text=chunk.text, score=score))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    @property
    def count(self) -> int:
        return len(self._chunks)
