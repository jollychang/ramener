from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentMetadata:
    date: Optional[str]
    source: Optional[str]
    title: Optional[str]
    confidence: Optional[float] = None


@dataclass
class GenerationResult:
    metadata: DocumentMetadata
    raw_response: str
