from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class ContentBlock(BaseModel):
    type: str = Field(default="text")
    label: str = Field(default="")
    text: str


class SlidePlan(BaseModel):
    slide_number: int
    intent: str
    title: str
    message: str = ""
    layout_hint: str = ""
    content_blocks: list[ContentBlock] = Field(default_factory=list)
    visual_direction: str = ""
    sources: list[str] = Field(default_factory=list)


class DeckMetadata(BaseModel):
    title: str
    audience: str = "General audience"
    tone: str = "Professional"
    template_id: str = "sample-board-template"
    slide_count: int | None = None


class DeckPlan(BaseModel):
    deck: DeckMetadata
    slides: list[SlidePlan]


class AnalyzeTemplateRequest(BaseModel):
    template_id: str = "sample-board-template"


class OnboardTemplateRequest(BaseModel):
    source_path: str
    template_id: str | None = None
    overwrite: bool = False


class ValidateDeckRequest(BaseModel):
    deck_path: str
    template_id: str = "sample-board-template"


class CreateDeckRequest(BaseModel):
    template_id: str = "sample-board-template"
    deck_plan: DeckPlan
    output_name: str | None = None


class CreateDeckResponse(BaseModel):
    artifact_path: str
    artifact_url: str
    template_id: str
    slide_count: int
    validation: dict[str, Any]
    slide_mapping: list[dict[str, Any]]


class ResponsesRequest(BaseModel):
    input: str | list[Any] | dict[str, Any] = ""
    template_id: str = "sample-board-template"
    slide_count: int = Field(default=6, ge=1, le=20)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    templates_dir: str
    output_dir: str


def as_posix_str(path: Path) -> str:
    return path.resolve().as_posix()
