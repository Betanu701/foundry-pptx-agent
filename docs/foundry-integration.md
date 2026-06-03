# Microsoft Foundry Integration

This repo can be used from Microsoft Foundry as a reusable PowerPoint-generation tool service.

## Recommended shape

Deploy this repo as a remote HTTPS service, then register its OpenAPI document in Foundry Tool Catalog / Toolbox.

```text
Foundry agent -> Foundry Toolbox/OpenAPI tool -> Foundry PPTX Agent service
```

Use this pattern when you want any Foundry agent to call the PowerPoint generator.

## One-repo deployment options

### Local Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Service URL: `http://localhost:8088`

OpenAPI URL: `http://localhost:8088/openapi.json`

### Azure Developer CLI starting point

The repo includes `azure.yaml` and a Dockerfile so it can be used as an Azure Container Apps service starting point:

```powershell
azd init --template https://github.com/Betanu701/foundry-pptx-agent
azd up
```

After deployment, set `PUBLIC_BASE_URL` to the public Container Apps endpoint so generated deck responses include absolute artifact links.

## Register in Foundry

1. Deploy the service to an HTTPS endpoint.
2. Open the OpenAPI document at:

   ```text
   https://<service-host>/openapi.json
   ```

3. In Foundry Tool Catalog / Toolbox, add an OpenAPI tool from that URL.
4. Enable the operations you want the agent to use:
   - `post_upload_template`
   - `post_analyze_template`
   - `post_create_deck`
   - `post_validate_deck`
   - `get_artifact`
5. In the agent instructions, tell the model:

   > Use the PowerPoint generator tool to onboard customer templates, generate deck plans, create PowerPoint artifacts, validate the result, and return the artifact URL.

## Tool operations

| Operation | Purpose |
| --- | --- |
| `POST /api/templates/upload` | Upload an existing `.pptx`, inspect master layouts, infer mappings, and create a template contract |
| `POST /api/templates/onboard` | Onboard a `.pptx` already accessible on the service filesystem |
| `POST /api/templates/analyze` | Inspect slide layouts/placeholders for an onboarded template |
| `POST /api/decks/create` | Generate a `.pptx` from structured deck-plan JSON |
| `POST /api/decks/validate` | Validate a generated artifact |
| `GET /api/artifacts/{filename}` | Download generated `.pptx` artifacts |

## Example agent instruction

```text
You are a presentation-generation agent. When the user asks for a PowerPoint deck:
1. Ask for or select a template.
2. If the user provides a PPTX template, call upload_template.
3. Create a concise structured deck plan.
4. Call create_deck with the chosen template_id and deck_plan.
5. Call validate_deck if needed.
6. Return the artifact_url and a short summary of the generated deck.
```

## Production hardening

Before customer production use:

- Put templates/generated decks in customer-controlled persistent storage.
- Add authentication, such as API Management in front of the service or Container Apps authentication.
- Set `PUBLIC_BASE_URL` to the public HTTPS service URL.
- Add visual rendering QA if PowerPoint/LibreOffice rendering is available in the deployment environment.
- Restrict upload size and accepted content types according to customer policy.

