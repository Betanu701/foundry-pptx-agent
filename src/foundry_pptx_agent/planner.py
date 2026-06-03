from __future__ import annotations

from .schemas import ContentBlock, DeckMetadata, DeckPlan, SlidePlan


def create_demo_plan(prompt: str, template_id: str, slide_count: int = 6) -> DeckPlan:
    topic = _topic_from_prompt(prompt)
    slides = [
        SlidePlan(
            slide_number=1,
            intent="title",
            title=topic,
            message=f"A polished executive briefing on {topic.lower()} for customer-ready discussion.",
            layout_hint="title",
        ),
        SlidePlan(
            slide_number=2,
            intent="executive_summary",
            title="Executive summary",
            message="The opportunity is meaningful, but durable value depends on focus, governance, and repeatable delivery.",
            layout_hint="content",
            content_blocks=[
                ContentBlock(type="takeaway", label="Opportunity", text="Prioritize workflows where speed, quality, or consistency can be measured."),
                ContentBlock(type="takeaway", label="Governance", text="Keep data, templates, and artifacts inside approved Microsoft boundaries."),
                ContentBlock(type="takeaway", label="Delivery", text="Start with a narrow pilot and expand after quality gates are proven."),
            ],
        ),
        SlidePlan(
            slide_number=3,
            intent="comparison",
            title="Reference experience vs. enterprise implementation",
            message="The goal is to preserve the polished deck-generation experience while adding enterprise controls.",
            layout_hint="comparison",
            content_blocks=[
                ContentBlock(type="comparison", label="Reference tools", text="Fast, polished artifact creation with strong narrative and visual variety."),
                ContentBlock(type="comparison", label="Foundry-native approach", text="Customer templates, governed tools, RBAC, traceability, evaluation, and controlled storage."),
            ],
        ),
        SlidePlan(
            slide_number=4,
            intent="timeline",
            title="Pilot delivery path",
            message="A focused pilot can show value quickly without overgeneralizing template support.",
            layout_hint="timeline",
            content_blocks=[
                ContentBlock(type="step", label="Discover", text="Choose the first deck type and approved template."),
                ContentBlock(type="step", label="Onboard", text="Create the template contract and layout catalog."),
                ContentBlock(type="step", label="Generate", text="Plan slides and render the deck deterministically."),
                ContentBlock(type="step", label="Validate", text="Run package, placeholder, and quality checks."),
            ],
        ),
        SlidePlan(
            slide_number=5,
            intent="risks",
            title="Risks to manage",
            message="The pilot should be explicit about template scope and artifact quality expectations.",
            layout_hint="content",
            content_blocks=[
                ContentBlock(type="risk", label="Template variability", text="Support a known layout catalog before arbitrary templates."),
                ContentBlock(type="risk", label="Visual overflow", text="Use concise generated copy and validate text lengths."),
                ContentBlock(type="risk", label="Ungrounded claims", text="Require source mapping for research-heavy presentations."),
            ],
        ),
        SlidePlan(
            slide_number=6,
            intent="conclusion",
            title="Recommended next step",
            message="Build a template-first Foundry prototype that creates a real PowerPoint artifact customers can inspect and edit.",
            layout_hint="title",
            content_blocks=[
                ContentBlock(type="callout", label="Decision", text="Approve a customer-template pilot with deterministic deck generation and validation."),
            ],
        ),
    ]
    selected = slides[:slide_count]
    for index, slide in enumerate(selected, start=1):
        slide.slide_number = index
    return DeckPlan(
        deck=DeckMetadata(
            title=topic,
            audience="Customer executive stakeholders",
            tone="Executive, concise, professional",
            template_id=template_id,
            slide_count=len(selected),
        ),
        slides=selected,
    )


def _topic_from_prompt(prompt: str) -> str:
    normalized = " ".join(prompt.split()).strip()
    if not normalized:
        return "Foundry PowerPoint Generation"
    if len(normalized) <= 72:
        return normalized[0].upper() + normalized[1:]
    return normalized[:69].rstrip() + "..."

