# Install And Deploy As An MCP Server

This guide explains how to run the Foundry PPTX Agent as a Model Context Protocol server instead of registering it as an OpenAPI tool.

The MCP deployment exposes PowerPoint-generation capabilities as MCP tools. It is a separate runtime from the FastAPI/OpenAPI service and uses `Dockerfile.mcp` plus `.env.mcp.deployment.example`.

For copy-ready agent instructions, use [AGENT_INSTRUCTIONS_EXAMPLES.md](AGENT_INSTRUCTIONS_EXAMPLES.md).

## What The MCP Server Provides

The MCP server wraps the same template and deck-generation services used by the API.

Available MCP tools:

| Tool | Purpose |
| --- | --- |
| `health` | Return runtime health and template/output paths. |
| `list_available_templates` | List templates available to the generator. |
| `analyze_powerpoint_template` | Inspect a template's layouts, placeholders, dimensions, and contract data. |
| `create_deck_from_prompt` | Create a deck from a plain-language request using the demo planner. |
| `create_deck_from_plan` | Create a deck from a structured deck-plan JSON object. |
| `validate_deck_artifact` | Validate a generated `.pptx` by filesystem path. |
| `onboard_template_from_path` | Onboard a `.pptx` file already available on the MCP server filesystem. |

Important artifact note:

- The MCP server returns generated `artifact_path` values for filesystem access.
- If `PUBLIC_BASE_URL` is set to a companion HTTP artifact service, generated results can also include absolute `artifact_url` values.
- If you deploy only the MCP server, plan how users will retrieve generated `.pptx` artifacts. Production deployments should use Blob Storage, SharePoint, OneDrive, or an authenticated artifact API.

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
- A Foundry or MCP-capable client that can connect to a remote streamable HTTP MCP server

## 1. Install Locally

```powershell
git clone <repo-url>
cd foundry-pptx-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python .\scripts\create_sample_template.py
python -m pytest
```

## 2. Run The MCP Server Locally

Run the MCP server with streamable HTTP transport:

```powershell
$env:MCP_TRANSPORT = "streamable-http"
$env:MCP_HOST = "127.0.0.1"
$env:MCP_PORT = "8089"
$env:TEMPLATES_DIR = "templates"
$env:OUTPUT_DIR = "generated"
$env:DEFAULT_TEMPLATE_ID = "sample-board-template"
python -m foundry_pptx_agent.mcp_server
```

Local MCP server URL:

```text
http://127.0.0.1:8089/mcp
```

For a local desktop MCP client that prefers stdio, run:

```powershell
$env:MCP_TRANSPORT = "stdio"
python -m foundry_pptx_agent.mcp_server
```

Example local MCP client configuration shape:

```json
{
  "mcpServers": {
    "foundry-pptx-agent": {
      "command": "python",
      "args": ["-m", "foundry_pptx_agent.mcp_server"],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "TEMPLATES_DIR": "templates",
        "OUTPUT_DIR": "generated",
        "DEFAULT_TEMPLATE_ID": "sample-board-template"
      }
    }
  }
}
```

The exact client configuration file and schema depend on the MCP client you use.

## 3. Configure MCP Deployment Environment

Copy the MCP deployment env template:

```powershell
Copy-Item .env.mcp.deployment.example .env.mcp.deployment
```

Edit `.env.mcp.deployment` and fill in values for the target environment.

Important variables:

| Variable | Purpose |
| --- | --- |
| `AZURE_SUBSCRIPTION_ID` | Target Azure subscription ID. |
| `AZURE_RESOURCE_GROUP` | Resource group to create or reuse. |
| `AZURE_LOCATION` | Azure region. |
| `AZURE_CONTAINER_REGISTRY_NAME` | Globally unique ACR name. |
| `AZURE_CONTAINER_APPS_ENVIRONMENT` | Container Apps environment name. |
| `AZURE_LOG_ANALYTICS_WORKSPACE` | Log Analytics workspace for Container Apps logs. |
| `AZURE_MANAGED_IDENTITY_NAME` | Identity used by Container Apps to pull from ACR. |
| `AZURE_CONTAINER_APP_NAME` | Container App name for the MCP server. |
| `IMAGE_NAME` | MCP container image repository name. |
| `IMAGE_TAG` | MCP image tag. |
| `DOCKERFILE_PATH` | Should be `Dockerfile.mcp`. |
| `MCP_TRANSPORT` | Use `streamable-http` for remote Container Apps deployment. |
| `MCP_PORT` | Defaults to `8089`. |
| `DEFAULT_TEMPLATE_ID` | Default template used by MCP tools. |
| `PUBLIC_BASE_URL` | Optional companion artifact API base URL. |
| `FOUNDRY_PROJECT_ENDPOINT` | Target Foundry project endpoint for documentation and registration. |

Do not commit `.env.mcp.deployment`; it is ignored by `.gitignore`.

Load `.env.mcp.deployment` into PowerShell:

```powershell
Get-Content .env.mcp.deployment | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object {
  $name, $value = $_ -split '=', 2
  [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}
```

## 4. Sign In And Prepare Azure

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

Create the resource group if needed:

```powershell
az group create `
  --name $env:AZURE_RESOURCE_GROUP `
  --location $env:AZURE_LOCATION
```

## 5. Create Azure Resources

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

## 6. Build And Push The MCP Container

Build using the MCP Dockerfile:

```powershell
az acr build `
  --registry $env:AZURE_CONTAINER_REGISTRY_NAME `
  --file $env:DOCKERFILE_PATH `
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

## 7. Deploy The MCP Server To Container Apps

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
  --target-port $env:MCP_PORT `
  --ingress external `
  --transport http `
  --user-assigned $identityId `
  --registry-server $loginServer `
  --registry-identity $identityId `
  --env-vars MCP_TRANSPORT=$env:MCP_TRANSPORT MCP_HOST=$env:MCP_HOST MCP_PORT=$env:MCP_PORT TEMPLATES_DIR=$env:TEMPLATES_DIR OUTPUT_DIR=$env:OUTPUT_DIR DEFAULT_TEMPLATE_ID=$env:DEFAULT_TEMPLATE_ID PUBLIC_BASE_URL=$env:PUBLIC_BASE_URL `
  --min-replicas $env:CONTAINERAPP_MIN_REPLICAS `
  --max-replicas $env:CONTAINERAPP_MAX_REPLICAS `
  --cpu $env:CONTAINERAPP_CPU `
  --memory $env:CONTAINERAPP_MEMORY
```

Capture the MCP server URL:

```powershell
$fqdn = az containerapp show `
  --name $env:AZURE_CONTAINER_APP_NAME `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --query properties.configuration.ingress.fqdn -o tsv

$mcpServerUrl = "https://$fqdn/mcp"
$mcpServerUrl
```

Add it back to `.env.mcp.deployment`:

```text
MCP_SERVER_URL=https://<container-app-fqdn>/mcp
```

## 8. Register The MCP Server With Foundry Or An MCP Client

Use the remote MCP server URL:

```text
https://<container-app-fqdn>/mcp
```

In a Foundry experience that supports MCP tools:

1. Open the target Foundry project.
2. Add a tool or connected server using MCP.
3. Choose streamable HTTP MCP transport if prompted.
4. Use the deployed MCP server URL.
5. Attach the MCP server to the agent that should generate PowerPoint decks.
6. Restrict tool access if the platform allows per-tool permissions.

If the target Foundry environment does not yet expose MCP registration in the UI, use the MCP endpoint with an MCP-capable client or gateway that Foundry can call. Do not register this MCP endpoint as an OpenAPI tool; use the OpenAPI deployment guide for that path.

## 9. Recommended Agent Instructions

Use instructions like these for an agent with MCP tool access:

```text
You are a presentation-generation agent. When the user asks for a PowerPoint deck, collect the topic, audience, slide count, and preferred template. Use the Foundry PPTX Agent MCP tools to list templates, create a deck, validate the artifact, and return the generated artifact path or URL. Use only templates returned by list_available_templates unless an administrator has onboarded a new template.
```

For user-facing agents, prefer these MCP tools:

- `list_available_templates`
- `create_deck_from_prompt`
- `create_deck_from_plan`
- `validate_deck_artifact`

Treat these as administrator or operator tools unless your policy says otherwise:

- `analyze_powerpoint_template`
- `onboard_template_from_path`

## 10. Production Notes For MCP

Before production use:

- Put authentication in front of the remote MCP endpoint.
- Avoid broad public unauthenticated MCP access.
- Store generated artifacts in persistent controlled storage.
- Use managed identity and Key Vault for Azure access and secrets.
- Restrict template onboarding to trusted operators.
- Add monitoring, audit logs, and retention policy.
- Decide whether artifact retrieval happens through a companion API, Blob Storage, SharePoint, or OneDrive.

See [PRODUCTION_SECURITY_TALK_TRACK.md](PRODUCTION_SECURITY_TALK_TRACK.md) for the broader production discussion guide.
