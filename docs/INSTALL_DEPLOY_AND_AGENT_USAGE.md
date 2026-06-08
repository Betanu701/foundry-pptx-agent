# Install, Deploy, And Use With Foundry Agents

This guide explains how to run the Foundry PPTX Agent locally, deploy it to Azure Container Apps, and register it as an OpenAPI tool for Microsoft Foundry agents.

The guide is intentionally generic. Fill in your own Azure subscription, resource group, region, Foundry project, and resource names in `.env.deployment` before deploying.

If you want to deploy the service as a Model Context Protocol server instead of an OpenAPI tool, use [INSTALL_DEPLOY_AS_MCP.md](INSTALL_DEPLOY_AS_MCP.md).

For copy-ready Foundry agent instructions, use [AGENT_INSTRUCTIONS_EXAMPLES.md](AGENT_INSTRUCTIONS_EXAMPLES.md).

## What This Service Does

Foundry PPTX Agent exposes an HTTPS API that can generate PowerPoint decks from approved templates. A Foundry agent can call it as an OpenAPI tool when a user asks for a deck.

Main capabilities:

- List available templates.
- Analyze or onboard PowerPoint templates.
- Generate `.pptx` files from a structured deck plan.
- Validate generated decks for package integrity and template issues.
- Return artifact URLs that agents can share with users.

## Requirements

Local development:

- Python 3.11 or newer
- PowerShell
- Git

Azure deployment:

- Azure CLI
- Permission to create or reuse:
  - Resource group
  - Azure Container Registry
  - Azure Container Apps environment
  - Log Analytics workspace
  - User-assigned managed identity
  - Role assignment for `AcrPull`
- Access to a Microsoft Foundry project where you can add OpenAPI tools

## 1. Clone And Install Locally

From a terminal:

```powershell
git clone <repo-url>
cd foundry-pptx-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Create or refresh the sample template:

```powershell
python .\scripts\create_sample_template.py
```

Run tests:

```powershell
python -m pytest
```

Start the API locally:

```powershell
python -m foundry_pptx_agent.app
```

The local API starts at:

```text
http://localhost:8088
```

Try a local generation request:

```powershell
curl.exe -X POST http://localhost:8088/responses `
  -H "Content-Type: application/json" `
  -d '{"input":"Create a customer-ready board deck about AI strategy","slide_count":6}'
```

Generated decks are written to `generated/`.

## 2. Configure Deployment Environment

Copy the deployment env template:

```powershell
Copy-Item .env.deployment.example .env.deployment
```

Edit `.env.deployment` and fill in values for your environment.

Important variables:

| Variable | Purpose |
| --- | --- |
| `AZURE_SUBSCRIPTION_ID` | Target Azure subscription ID. |
| `AZURE_TENANT_ID` | Optional tenant ID for documentation and validation. |
| `AZURE_RESOURCE_GROUP` | Resource group to create or reuse. |
| `AZURE_LOCATION` | Azure region, such as `eastus2`. |
| `AZURE_CONTAINER_REGISTRY_NAME` | Globally unique ACR name. Lowercase letters and numbers only. |
| `AZURE_CONTAINER_APPS_ENVIRONMENT` | Container Apps environment name. |
| `AZURE_LOG_ANALYTICS_WORKSPACE` | Log Analytics workspace for Container Apps logs. |
| `AZURE_MANAGED_IDENTITY_NAME` | User-assigned identity used by Container Apps to pull from ACR. |
| `AZURE_CONTAINER_APP_NAME` | Container App name. |
| `IMAGE_NAME` | Container image repository name. |
| `IMAGE_TAG` | Image tag for this deployment. |
| `DEFAULT_TEMPLATE_ID` | Template ID used when callers do not specify one. |
| `FOUNDRY_AI_SERVICES_RESOURCE` | AI Services resource that hosts the Foundry project. |
| `FOUNDRY_PROJECT_NAME` | Foundry project name. |
| `FOUNDRY_PROJECT_ENDPOINT` | Project endpoint URL. |

Do not commit `.env.deployment`; it is ignored by `.gitignore`.

Load `.env.deployment` into the current PowerShell session:

```powershell
Get-Content .env.deployment | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object {
  $name, $value = $_ -split '=', 2
  [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}
```

## 3. Sign In And Prepare Azure

Sign in:

```powershell
az login
az account set --subscription $env:AZURE_SUBSCRIPTION_ID
az account show --output table
```

Register providers if needed:

```powershell
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.ManagedIdentity
```

Create the resource group if it does not exist:

```powershell
az group create `
  --name $env:AZURE_RESOURCE_GROUP `
  --location $env:AZURE_LOCATION
```

## 4. Create Azure Resources

Create Azure Container Registry:

```powershell
az acr create `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --name $env:AZURE_CONTAINER_REGISTRY_NAME `
  --sku Basic `
  --location $env:AZURE_LOCATION `
  --admin-enabled false
```

Create Log Analytics workspace:

```powershell
az monitor log-analytics workspace create `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --workspace-name $env:AZURE_LOG_ANALYTICS_WORKSPACE `
  --location $env:AZURE_LOCATION
```

Create Container Apps environment:

```powershell
$workspaceId = az monitor log-analytics workspace show `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --workspace-name $env:AZURE_LOG_ANALYTICS_WORKSPACE `
  --query customerId -o tsv

$workspaceKey = az monitor log-analytics workspace get-shared-keys `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --workspace-name $env:AZURE_LOG_ANALYTICS_WORKSPACE `
  --query primarySharedKey -o tsv

az containerapp env create `
  --name $env:AZURE_CONTAINER_APPS_ENVIRONMENT `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --location $env:AZURE_LOCATION `
  --logs-workspace-id $workspaceId `
  --logs-workspace-key $workspaceKey
```

Create the managed identity:

```powershell
az identity create `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --name $env:AZURE_MANAGED_IDENTITY_NAME `
  --location $env:AZURE_LOCATION
```

## 5. Build And Push The Container Image

The Dockerfile uses a Microsoft Container Registry Python base image so Azure cloud builds do not depend on Docker Hub rate limits.

Build with ACR Tasks:

```powershell
az acr build `
  --registry $env:AZURE_CONTAINER_REGISTRY_NAME `
  --image "$($env:IMAGE_NAME):$($env:IMAGE_TAG)" `
  .
```

Grant the Container App identity permission to pull from ACR:

```powershell
$principalId = az identity show `
  --name $env:AZURE_MANAGED_IDENTITY_NAME `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --query principalId -o tsv

$identityId = az identity show `
  --name $env:AZURE_MANAGED_IDENTITY_NAME `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --query id -o tsv

$acrId = az acr show `
  --name $env:AZURE_CONTAINER_REGISTRY_NAME `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --query id -o tsv

az role assignment create `
  --assignee-object-id $principalId `
  --assignee-principal-type ServicePrincipal `
  --role AcrPull `
  --scope $acrId
```

## 6. Deploy The Container App

```powershell
$loginServer = az acr show `
  --name $env:AZURE_CONTAINER_REGISTRY_NAME `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --query loginServer -o tsv

$identityId = az identity show `
  --name $env:AZURE_MANAGED_IDENTITY_NAME `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --query id -o tsv

az containerapp create `
  --name $env:AZURE_CONTAINER_APP_NAME `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --environment $env:AZURE_CONTAINER_APPS_ENVIRONMENT `
  --image "$loginServer/$($env:IMAGE_NAME):$($env:IMAGE_TAG)" `
  --target-port 8088 `
  --ingress external `
  --transport auto `
  --user-assigned $identityId `
  --registry-server $loginServer `
  --registry-identity $identityId `
  --env-vars TEMPLATES_DIR=$env:TEMPLATES_DIR OUTPUT_DIR=$env:OUTPUT_DIR DEFAULT_TEMPLATE_ID=$env:DEFAULT_TEMPLATE_ID PUBLIC_BASE_URL= `
  --min-replicas $env:CONTAINERAPP_MIN_REPLICAS `
  --max-replicas $env:CONTAINERAPP_MAX_REPLICAS `
  --cpu $env:CONTAINERAPP_CPU `
  --memory $env:CONTAINERAPP_MEMORY
```

Capture the service URL and update `PUBLIC_BASE_URL`:

```powershell
$fqdn = az containerapp show `
  --name $env:AZURE_CONTAINER_APP_NAME `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --query properties.configuration.ingress.fqdn -o tsv

$serviceUrl = "https://$fqdn"
$openApiUrl = "$serviceUrl/openapi.json"

az containerapp update `
  --name $env:AZURE_CONTAINER_APP_NAME `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --set-env-vars PUBLIC_BASE_URL=$serviceUrl TEMPLATES_DIR=$env:TEMPLATES_DIR OUTPUT_DIR=$env:OUTPUT_DIR DEFAULT_TEMPLATE_ID=$env:DEFAULT_TEMPLATE_ID
```

Add these values back to `.env.deployment` for your records:

```text
SERVICE_URL=https://<container-app-fqdn>
OPENAPI_URL=https://<container-app-fqdn>/openapi.json
```

## 7. Verify The Deployment

Health check:

```powershell
curl.exe "$serviceUrl/health"
```

OpenAPI check:

```powershell
curl.exe "$openApiUrl"
```

Generate a smoke-test deck:

```powershell
$body = @{
  input = "Create a concise board deck about the PowerPoint generator"
  slide_count = 3
} | ConvertTo-Json

curl.exe -X POST "$serviceUrl/responses" `
  -H "Content-Type: application/json" `
  -d $body
```

The response should include:

- `status` equal to `completed`
- `metadata.artifact_url` containing a downloadable `.pptx` URL
- `metadata.validation.ok` equal to `true`

Download the artifact:

```powershell
curl.exe -L "<artifact-url>" -o smoke-test.pptx
```

## 8. Register The OpenAPI Tool In Microsoft Foundry

Open your Microsoft Foundry project and add the deployed API as an OpenAPI tool.

Use this OpenAPI URL:

```text
https://<container-app-fqdn>/openapi.json
```

Recommended operations to enable:

| Operation ID | Purpose |
| --- | --- |
| `get_templates_api_templates_get` | List templates available to the service. |
| `post_analyze_template_api_templates_analyze_post` | Inspect template layouts and placeholders. |
| `post_create_deck_api_decks_create_post` | Generate a deck from a structured deck plan. |
| `post_validate_deck_api_decks_validate_post` | Validate a generated artifact. |
| `get_artifact_api_artifacts__filename__get` | Download generated artifacts. |
| `post_upload_template_api_templates_upload_post` | Upload a template, if your security policy allows it. |
| `post_onboard_template_api_templates_onboard_post` | Onboard a template already available to the service filesystem. |

You can also expose `responses_responses_post` for a simple Foundry/OpenAI Responses-style demo flow.

## 9. Recommended Agent Instructions

Use instructions like these in the Foundry agent that has access to the OpenAPI tool:

```text
You are a presentation-generation agent. When the user asks for a PowerPoint deck, gather the audience, topic, desired slide count, and any required template. Use the PowerPoint generator tool to list or select templates, create a concise structured deck plan, call the deck creation operation, validate the result when appropriate, and return the generated artifact URL with a short summary of the deck.
```

For stricter enterprise behavior, add:

```text
Use only approved templates returned by the PowerPoint generator tool. Do not invent template IDs. If validation returns errors, explain the issue and retry with a corrected deck plan before returning the artifact URL.
```

## 10. Typical Agent Flow

1. User asks for a PowerPoint deck.
2. Agent asks clarifying questions if topic, audience, template, or slide count is missing.
3. Agent calls `get_templates_api_templates_get` to inspect available templates.
4. Agent creates a structured deck plan.
5. Agent calls `post_create_deck_api_decks_create_post`.
6. Agent calls `post_validate_deck_api_decks_validate_post` if validation was not already included or if policy requires a second check.
7. Agent returns `metadata.artifact_url` or the artifact URL from the create response.

## 11. Template Onboarding

For a customer template, import it before building the container image:

```powershell
python .\scripts\import_template.py "C:\path\to\customer-template.pptx" --template-id customer-master-template --overwrite
```

This writes:

- `templates/customer-master-template.pptx`
- `templates/customer-master-template.contract.json`

Do not commit customer-confidential templates unless your repository policy allows it. The default `.gitignore` excludes `templates/customer-*.pptx` and `templates/customer-*.contract.json`.

## 12. Production Hardening Checklist

For a stakeholder-oriented discussion guide, see [PRODUCTION_SECURITY_TALK_TRACK.md](PRODUCTION_SECURITY_TALK_TRACK.md).

Before production use:

- Put generated decks in persistent storage such as Azure Blob Storage, SharePoint, or OneDrive.
- Add authentication in front of the public API, such as Azure API Management or Container Apps authentication.
- Review whether template upload should be enabled for agents.
- Add size limits and content-type restrictions for uploads.
- Use private networking if your Foundry project and enterprise policy require it.
- Add monitoring and alerting for Container Apps revisions, failed requests, and storage usage.
- Add evaluation cases for template fidelity, placeholder leakage, content quality, and artifact validation.
