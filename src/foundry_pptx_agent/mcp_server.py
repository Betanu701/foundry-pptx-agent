from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .planner import create_demo_plan
from .pptx_service import analyze_template, create_deck, list_templates, validate_deck
from .schemas import CreateDeckRequest, DeckPlan
from .settings import DEFAULT_TEMPLATE_ID, OUTPUT_DIR, TEMPLATES_DIR, ensure_runtime_dirs
from .template_onboarding import onboard_template

ensure_runtime_dirs()

mcp = FastMCP(
    "Foundry PPTX Agent",
    instructions=(
        "Generate PowerPoint decks from approved templates. Use list_templates before creating decks, "
        "create_deck_from_prompt for simple requests, create_deck_from_plan for structured plans, "
        "and validate_deck_artifact before returning generated artifacts to users."
    ),
)


@mcp.tool()
def health() -> dict[str, str]:
    """Return service health and runtime paths."""
    return {
        "status": "ok",
        "templates_dir": str(TEMPLATES_DIR),
        "output_dir": str(OUTPUT_DIR),
    }


@mcp.tool()
def list_available_templates() -> dict[str, Any]:
    """List PowerPoint templates available to the generator."""
    return {"templates": list_templates()}


@mcp.tool()
def analyze_powerpoint_template(template_id: str = DEFAULT_TEMPLATE_ID) -> dict[str, Any]:
    """Inspect layouts, placeholders, dimensions, and contract data for a template."""
    return analyze_template(template_id)


@mcp.tool()
def create_deck_from_prompt(
    prompt: str,
    template_id: str = DEFAULT_TEMPLATE_ID,
    slide_count: int = 6,
    output_name: str | None = None,
) -> dict[str, Any]:
    """Create a PowerPoint deck from a plain-language prompt using the demo planner."""
    if slide_count < 1 or slide_count > 20:
        raise ValueError("slide_count must be between 1 and 20")
    deck_plan = create_demo_plan(prompt, template_id, slide_count)
    result = create_deck(CreateDeckRequest(template_id=template_id, deck_plan=deck_plan, output_name=output_name))
    return result.model_dump()


@mcp.tool()
def create_deck_from_plan(
    deck_plan: dict[str, Any],
    template_id: str = DEFAULT_TEMPLATE_ID,
    output_name: str | None = None,
) -> dict[str, Any]:
    """Create a PowerPoint deck from a structured deck-plan JSON object."""
    parsed_plan = DeckPlan.model_validate(deck_plan)
    result = create_deck(CreateDeckRequest(template_id=template_id, deck_plan=parsed_plan, output_name=output_name))
    return result.model_dump()


@mcp.tool()
def validate_deck_artifact(deck_path: str, template_id: str = DEFAULT_TEMPLATE_ID) -> dict[str, Any]:
    """Validate a generated PowerPoint artifact by filesystem path."""
    return validate_deck(deck_path, template_id)


@mcp.tool()
def onboard_template_from_path(
    source_path: str,
    template_id: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Onboard a .pptx template that is already accessible on the MCP server filesystem."""
    return onboard_template(Path(source_path), template_id, overwrite)


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8089"))
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
