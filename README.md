# Foundry PPTX Agent

Foundry PPTX Agent is a ready-to-run prototype for generating polished PowerPoint decks from approved customer templates inside a Microsoft Foundry-style architecture.

The repo demonstrates the recommended pattern:

- A presentation agent owns intake, planning, revision, and Foundry-style `/responses` interaction.
- A deterministic PowerPoint generator creates the actual `.pptx` artifact from a customer template.
- Template contracts, validation, and artifact metadata provide the enterprise governance seams customers will need.

This prototype runs locally without Azure credentials. The included `agent.yaml` and `.foundry/agent-metadata.yaml` are contract-first starting points for hosted-agent deployment and should be validated against the customer's Foundry environment before production use.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python .\scripts\create_sample_template.py
python -m foundry_pptx_agent.app
```

The service starts on `http://localhost:8088`.

In another terminal:

```powershell
curl.exe -X POST http://localhost:8088/responses `
  -H "Content-Type: application/json" `
  -d "{\"input\":\"Create a customer-ready board deck about AI strategy in Microsoft Foundry\",\"slide_count\":6}"
```

The generated `.pptx` is written to `generated\`.

## API surface

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service health and runtime paths |
| `GET /api/templates` | List available `.pptx` templates |
| `POST /api/templates/analyze` | Inspect slide layouts and placeholders |
| `POST /api/decks/create` | Generate a `.pptx` from a structured deck plan |
| `POST /api/decks/validate` | Validate package integrity, placeholder leakage, and text-length risk |
| `POST /responses` | Foundry/OpenAI Responses-style demo endpoint |

## Generate from a structured plan

```powershell
$body = Get-Content .\examples\sample_deck_plan.json -Raw
$payload = @{
  template_id = "sample-board-template"
  deck_plan = ($body | ConvertFrom-Json)
  output_name = "customer-demo.pptx"
} | ConvertTo-Json -Depth 20

curl.exe -X POST http://localhost:8088/api/decks/create `
  -H "Content-Type: application/json" `
  -d $payload
```

## Template model

The generator opens the customer template as the base `Presentation` and adds slides from that template's layouts. That preserves masters, themes, layouts, and embedded template definitions as far as `python-pptx` supports.

For each template, add:

- `templates\<template-id>.pptx`
- `templates\<template-id>.contract.json`

The contract defines brand colors, supported intents, text limits, and required footer text. The sample files show the expected shape.

## MVP limitations

- The prototype uses layout-based template reuse, not arbitrary slide XML duplication.
- Charts, SmartArt, grouped shapes, and complex picture placeholders need template-specific handling.
- Visual overflow checks are heuristic; PowerPoint rendering should be part of a production QA loop.
- Macro-enabled `.pptm` templates are intentionally not supported.
- The `/responses` endpoint follows the practical response shape needed for a local demo, not a full production Foundry hosting adapter.

## Foundry production path

Recommended hardening before a customer pilot:

1. Replace the deterministic demo planner with a Foundry-hosted model workflow that emits the same deck-plan JSON schema.
2. Store templates and generated decks in customer-controlled Blob Storage, SharePoint, or OneDrive.
3. Expose the generator as a Foundry Toolbox/MCP or OpenAPI tool.
4. Add source grounding through Azure AI Search or File Search.
5. Add visual rendering QA and Foundry evaluation datasets for content quality, template fidelity, and brand compliance.
6. Deploy the service as a Foundry hosted agent or as a tool service called by the hosted agent.

## Test

```powershell
python .\scripts\create_sample_template.py
pytest
```

