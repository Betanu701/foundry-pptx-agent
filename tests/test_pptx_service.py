from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from foundry_pptx_agent.app import app
from foundry_pptx_agent.planner import create_demo_plan
from foundry_pptx_agent.pptx_service import create_deck, validate_deck
from foundry_pptx_agent.schemas import CreateDeckRequest, DeckPlan


ROOT = Path(__file__).resolve().parents[1]


def _sample_plan() -> DeckPlan:
    with (ROOT / "examples" / "sample_deck_plan.json").open("r", encoding="utf-8") as handle:
        return DeckPlan.model_validate(json.load(handle))


def test_analyze_sample_template() -> None:
    client = TestClient(app)
    response = client.post("/api/templates/analyze", json={"template_id": "sample-board-template"})
    assert response.status_code == 200
    body = response.json()
    assert body["template_id"] == "sample-board-template"
    assert body["layout_count"] > 0


def test_create_and_validate_deck() -> None:
    result = create_deck(
        CreateDeckRequest(
            template_id="sample-board-template",
            deck_plan=_sample_plan(),
            output_name="pytest-generated-deck.pptx",
        )
    )
    assert result.slide_count == 6
    assert result.validation["ok"] is True
    assert Path(result.artifact_path).exists()


def test_validate_detects_placeholder_text(tmp_path: Path) -> None:
    result = create_deck(
        CreateDeckRequest(
            template_id="sample-board-template",
            deck_plan=_sample_plan(),
            output_name="pytest-placeholder-check.pptx",
        )
    )
    validation = validate_deck(result.artifact_path, "sample-board-template")
    assert validation["ok"] is True


def test_responses_endpoint_creates_artifact() -> None:
    client = TestClient(app)
    response = client.post(
        "/responses",
        json={"input": "Create a board deck about Foundry PowerPoint generation", "slide_count": 4},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert Path(body["metadata"]["artifact_path"]).exists()


def test_implementation_overview_prompt_uses_specific_plan() -> None:
    plan = create_demo_plan(
        "Create a customer-ready overview deck of our Foundry PPTX Agent implementation.",
        "sample-board-template",
        6,
    )
    assert plan.deck.title == "Foundry PPTX Agent Overview"
    assert [slide.title for slide in plan.slides] == [
        "Foundry PPTX Agent Overview",
        "What we implemented",
        "Architecture split",
        "How the demo runs",
        "Validation and guardrails",
        "Production hardening path",
    ]
