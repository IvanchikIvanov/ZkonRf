from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class TemplateField:
    field_id: str
    label: str
    prompt: str
    required: bool = True


@dataclass(frozen=True)
class DocumentTemplate:
    template_id: str
    title: str
    keywords: tuple[str, ...]
    required_fields: tuple[TemplateField, ...]
    optional_fields: tuple[TemplateField, ...] = ()
    filename_prefix: str = "document"


@dataclass
class DraftState:
    user_id: int
    template_id: str
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentResult:
    status: Literal["not_document", "ask_fields", "ready", "error"]
    message: str
    file_path: Path | None = None
    filename: str | None = None
