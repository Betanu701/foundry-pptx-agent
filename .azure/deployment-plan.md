# Deployment Plan: Foundry PPTX Agent

Status: Template - Fill For Target Environment

## 1. Goal

Deploy the Foundry PPTX Agent to Azure as a public HTTPS service and connect it to a Microsoft Foundry project as an OpenAPI tool.

## 2. Current App

- Python FastAPI service packaged with Docker.
- Runtime port: 8088.
- Azure target: Azure Container Apps.
- Foundry integration target: register deployed `/openapi.json` in Foundry Tool Catalog or Toolbox.

## 3. Azure Context

Fill these values in `.env.deployment` before deployment:

- Subscription ID: `<subscription-id>`
- Tenant ID: `<tenant-id>`
- Location: `<azure-region>`
- Resource group: `<resource-group>`
- Foundry AI Services resource: `<ai-services-resource-name>`
- Foundry project: `<foundry-project-name>`
- Foundry project endpoint: `https://<ai-services-resource>.services.ai.azure.com/api/projects/<project-name>`

## 4. Planned Architecture

- Azure Resource Group
- Azure Container Registry
- Log Analytics workspace
- Azure Container Apps Environment
- User-assigned managed identity
- Azure Container App running the Dockerized FastAPI service
- Public HTTPS ingress on port 8088
- Environment variables:
  - `TEMPLATES_DIR=templates`
  - `OUTPUT_DIR=generated`
  - `DEFAULT_TEMPLATE_ID=sample-board-template`
  - `PUBLIC_BASE_URL=https://<container-app-fqdn>`

## 5. Deployment Recipe

Use Azure CLI and Azure Container Apps commands from the authenticated Azure CLI session. Load deployment values from `.env.deployment`, build and push the container image to ACR, then create or update the Container App.

Primary guide: `docs/INSTALL_DEPLOY_AND_AGENT_USAGE.md`.

Quick runbook: `docs/azure-foundry-deployment-runbook.md`.

## 6. Validation Plan

- Confirm local tests pass.
- Confirm Azure CLI account and subscription.
- Confirm required Azure providers are registered.
- Confirm ACR image build succeeds.
- Confirm Container App provisioning state is `Succeeded` and running status is `Running`.
- Verify `/health` from the deployed HTTPS endpoint.
- Verify `/openapi.json` is reachable.
- Call `/responses` to generate a sample artifact.
- Download the generated `.pptx` artifact.

## 7. Validation Proof

Fill after deployment:

- Local tests: `<command and result>`
- ACR image: `<login-server>/<image-name>:<image-tag>`
- Container App: `<container-app-name>`
- Service URL: `https://<container-app-fqdn>`
- OpenAPI URL: `https://<container-app-fqdn>/openapi.json`
- Smoke test result: `<result>`
- Foundry registration: `<tool name or registration notes>`

## 8. Foundry Connection Plan

- Open the target Foundry project.
- Register `https://<container-app-fqdn>/openapi.json` as an OpenAPI tool.
- Enable the operations needed by the agent.
- Add the OpenAPI tool to the target Foundry agent.
- Add agent instructions from `docs/INSTALL_DEPLOY_AND_AGENT_USAGE.md`.

## 9. Handoff Documentation

- `.env.deployment.example` contains the deployment environment template.
- `docs/INSTALL_DEPLOY_AND_AGENT_USAGE.md` contains end-to-end install, deploy, and agent usage instructions.
- `docs/azure-foundry-deployment-runbook.md` contains a shorter deployment runbook.
