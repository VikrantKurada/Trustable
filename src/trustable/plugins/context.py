from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InteractionContext:
    """State threaded through the runtime pipeline for one LLM interaction."""

    prompt: Any
    response: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    records: list[dict[str, Any]] = field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
