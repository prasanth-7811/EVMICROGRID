"""Small deterministic lexical retriever over the local policy knowledge base."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .config import POLICY_FILE
from .schemas import PolicyEvidence

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.lower()))


@dataclass(frozen=True)
class PolicyDocument:
    policy_id: str
    title: str
    source: str
    tags: tuple[str, ...]
    text: str


class PolicyRetriever:
    """Retrieve policy snippets with no network calls or embedding service."""

    def __init__(self, path: str | Path = POLICY_FILE) -> None:
        self.path = Path(path)
        self.documents = self._load()

    def _load(self) -> tuple[PolicyDocument, ...]:
        with self.path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        documents = []
        for item in raw:
            documents.append(
                PolicyDocument(
                    policy_id=str(item["policy_id"]),
                    title=str(item["title"]),
                    source=str(item["source"]),
                    tags=tuple(str(tag) for tag in item.get("tags", [])),
                    text=str(item["text"]),
                )
            )
        return tuple(documents)

    def retrieve(self, query: str, top_k: int = 3) -> list[PolicyEvidence]:
        query_terms = _tokens(query)
        ranked: list[tuple[float, int, PolicyDocument, list[str]]] = []
        for index, document in enumerate(self.documents):
            title_terms = _tokens(document.title)
            tag_terms = _tokens(" ".join(document.tags))
            text_terms = _tokens(document.text)
            matched = sorted(query_terms & (title_terms | tag_terms | text_terms))
            score = (
                len(query_terms & title_terms) * 3.0
                + len(query_terms & tag_terms) * 2.0
                + len(query_terms & text_terms) * 0.5
            )
            # Keep a stable, useful fallback ordering when the query is sparse.
            ranked.append((score, index, document, matched))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        selected = ranked[: max(1, min(int(top_k), len(ranked)))]
        return [
            PolicyEvidence(
                policy_id=document.policy_id,
                title=document.title,
                source=document.source,
                snippet=document.text[:240],
                score=round(max(0.0, score), 3),
                matched_terms=matched,
            )
            for score, _, document, matched in selected
        ]

    def all_documents(self) -> list[PolicyEvidence]:
        return self.retrieve("charging safety renewable tariff governance", len(self.documents))
