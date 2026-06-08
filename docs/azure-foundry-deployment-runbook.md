# Azure + Microsoft Foundry Deployment Runbook

This runbook describes how to deploy the Foundry PPTX Agent to Azure Container Apps and register it with a Microsoft Foundry project as an OpenAPI tool.

This document is sanitized for handoff. It does not contain tenant IDs, subscription IDs, live service URLs, or customer-specific Foundry project names. Put environment-specific values in `.env.deployment`, using `.env.deployment.example` as the template.

For the full install, deployment, and agent usage guide, see [INSTALL_DEPLOY_AND_AGENT_USAGE.md](INSTALL_DEPLOY_AND_AGENT_USAGE.md).

For an MCP server deployment path, see [INSTALL_DEPLOY_AS_MCP.md](INSTALL_DEPLOY_AS_MCP.md).

For copy-ready agent instructions, see [AGENT_INSTRUCTIONS_EXAMPLES.md](AGENT_INSTRUCTIONS_EXAMPLES.md).

For production security discussion points, see [PRODUCTION_SECURITY_TALK_TRACK.md](PRODUCTION_SECURITY_TALK_TRACK.md).

## Deployment Configuration

Copy and fill the deployment environment file:

```powershell
Copy-Item .env.deployment.example .env.deployment
```

Required values include:

- `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`
- `AZURE_LOCATION`
- `AZURE_CONTAINER_REGISTRY_NAME`
- `AZURE_CONTAINER_APPS_ENVIRONMENT`
- `AZURE_LOG_ANALYTICS_WORKSPACE`
- `AZURE_MANAGED_IDENTITY_NAME`
- `AZURE_CONTAINER_APP_NAME`
- `FOUNDRY_AI_SERVICES_RESOURCE`
- `FOUNDRY_PROJECT_NAME`
- `FOUNDRY_PROJECT_ENDPOINT`

Load the values into PowerShell:

```powershell
Get-Content .env.deployment | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object {
  $name, $value = $_ -split '=', 2
  [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}
```

## What Changed In The App

The Docker base image uses Microsoft Container Registry:

```text
mcr.microsoft.com/devcontainers/python:1-3.12-bookworm
```

This avoids Docker Hub unauthenticated pull-rate limits during Azure Container Registry Tasks builds.

## Prerequisites

Install and sign in to these tools:

- Azure CLI
- Azure Container Apps Azure CLI command group
- Permission to create Azure Container Registry, managed identity, role assignments, and Container Apps resources
- Access to the target Microsoft Foundry project

Confirm Azure login:

```powershell
az login
az account set --subscription $env:AZURE_SUBSCRIPTION_ID
az account show --output table
```

Register required providers if they are not already registered:

```powershell
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.ManagedIdentity
```

## Local Validation

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python .\scripts\create_sample_template.py
python -m pytest
```

Expected result: tests pass.

## Provision Azure Resources

Create or reuse a resource group:

```powershell
az group create `
  --name $env:AZURE_RESOURCE_GROUP `
  --location $env:AZURE_LOCATION
```

Create ACR:

```powershell
az acr create `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --name $env:AZURE_CONTAINER_REGISTRY_NAME `
  --sku Basic `
  --location $env:AZURE_LOCATION `
  --admin-enabled false
```

Create Log Analytics:

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

## Build And Push The Image

```powershell
az acr build `
  --registry $env:AZURE_CONTAINER_REGISTRY_NAME `
  --image "$($env:IMAGE_NAME):$($env:IMAGE_TAG)" `
  .
```

Grant ACR pull permissions:

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

## Create The Container App

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

Capture the generated hostname and set `PUBLIC_BASE_URL`:

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

Store these generated values in `.env.deployment` for future redeployments:

```text
SERVICE_URL=https://<container-app-fqdn>
OPENAPI_URL=https://<container-app-fqdn>/openapi.json
```

## Verify The Deployment

Health check:

```powershell
curl.exe "$serviceUrl/health"
```

Expected shape:

```json
{"status":"ok","templates_dir":"/app/templates","output_dir":"/app/generated"}
```

OpenAPI check:

```powershell
curl.exe "$openApiUrl"
```

Generate a sample deck:

```powershell
$body = @{
  input = "Create a concise board deck about the PowerPoint generator"
  slide_count = 3
} | ConvertTo-Json

curl.exe -X POST "$serviceUrl/responses" `
  -H "Content-Type: application/json" `
  -d $body
```

The response should have `status` set to `completed` and `metadata.artifact_url` set to a URL under `$serviceUrl/api/artifacts/`.

## Register With Microsoft Foundry

The deployed app is exposed to Foundry through its OpenAPI document:

```text
https://<container-app-fqdn>/openapi.json
```

In Microsoft Foundry:

1. Open the target project.
2. Go to Tool Catalog or Toolbox.
3. Add a new OpenAPI tool.
4. Use the deployed OpenAPI URL.
5. Select the operations the agent should be allowed to call:
   - `get_templates_api_templates_get`
   - `post_analyze_template_api_templates_analyze_post`
   - `post_create_deck_api_decks_create_post`
   - `post_validate_deck_api_decks_validate_post`
   - `get_artifact_api_artifacts__filename__get`
   - `post_upload_template_api_templates_upload_post` if template upload is allowed
   - `post_onboard_template_api_templates_onboard_post` if the agent can onboard templates already available to the service
6. Add the tool to the desired Foundry agent.
7. Add agent instructions from [INSTALL_DEPLOY_AND_AGENT_USAGE.md](INSTALL_DEPLOY_AND_AGENT_USAGE.md).

## Operational Notes

- Generated files are stored in the container filesystem under `/app/generated`. For production, replace this with Blob Storage, SharePoint, or another persistent store.
- The service currently has public ingress and no application-layer authentication. For production, put Azure API Management, Container Apps authentication, or another authorization layer in front of it.
- The app supports templates packaged in the image under `/app/templates`. For customer-specific templates, import them before building the image or add persistent storage and an authenticated upload flow.
- Keep ACR admin access disabled. The Container App uses managed identity and `AcrPull`.
- If ACR image pulls fail immediately after role assignment, wait for RBAC propagation and retry the Container App revision.
