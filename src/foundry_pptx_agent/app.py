from __future__ import annotations

import time
import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException

from .planner import create_demo_plan
from .pptx_service import analyze_template, create_deck, list_templates, validate_deck
from .schemas import (
    AnalyzeTemplateRequest,
    CreateDeckRequest,
    HealthResponse,
    ResponsesRequest,
    ValidateDeckRequest,
)
from .settings import DEFAULT_TEMPLATE_ID, OUTPUT_DIR, TEMPLATES_DIR, ensure_runtime_dirs

ensure_runtime_dirs()

app = FastAPI(
    title="Foundry PPTX Agent",
    description="Foundry-style presentation agent and deterministic PowerPoint generator for approved templates.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", templates_dir=str(TEMPLATES_DIR), output_dir=str(OUTPUT_DIR))


@app.get("/api/templates")
def get_templates() -> dict[str, Any]:
    return {"templates": list_templates()}


@app.post("/api/templates/analyze")
def post_analyze_template(request: AnalyzeTemplateRequest) -> dict[str, Any]:
    try:
        return analyze_template(request.template_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/decks/create")
def post_create_deck(request: CreateDeckRequest) -> dict[str, Any]:
    try:
        return create_deck(request).model_dump()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/decks/validate")
def post_validate_deck(request: ValidateDeckRequest) -> dict[str, Any]:
    return validate_deck(request.deck_path, request.template_id)


@app.post("/responses")
def responses(request: ResponsesRequest) -> dict[str, Any]:
    prompt = _extract_prompt(request.input)
    template_id = request.template_id or DEFAULT_TEMPLATE_ID
    deck_plan = create_demo_plan(prompt, template_id, request.slide_count)
    result = create_deck(CreateDeckRequest(template_id=template_id, deck_plan=deck_plan))
    text = (
        f"Created {result.slide_count}-slide PowerPoint deck '{deck_plan.deck.title}'. "
        f"Artifact: {result.artifact_path}. "
        f"Validation: {'passed' if result.validation.get('ok') else 'needs review'}."
    )
    return {
        "id": f"resp_{uuid.uuid4().hex}",
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "output": [
            {
                "id": f"msg_{uuid.uuid4().hex}",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
        "metadata": {
            "artifact_path": result.artifact_path,
            "template_id": result.template_id,
            "slide_count": result.slide_count,
            "validation": result.validation,
            "slide_mapping": result.slide_mapping,
        },
    }


def _extract_prompt(value: str | list[Any] | dict[str, Any]) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "content", "prompt"):
            if key in value:
                return str(value[key])
        return str(value)
    parts: list[str] = []
    for item in value:
        if isinstance(item, dict):
            parts.append(str(item.get("text") or item.get("content") or item))
        else:
            parts.append(str(item))
    return " ".join(parts)


def main() -> None:
    uvicorn.run("foundry_pptx_agent.app:app", host="0.0.0.0", port=8088)


if __name__ == "__main__":
    main()

