# Production Security Talk Track

This document is a discussion guide for teams evaluating the Foundry PPTX Agent for production use. It describes the security posture to explain, the risks to call out, and the controls a production implementation should add.

It is intentionally a talk track, not an implementation plan. Use it with architects, security reviewers, platform teams, and application owners before moving beyond a pilot.

## Executive Summary

The current service is a prototype-friendly PowerPoint generation tool that can be deployed behind a public HTTPS endpoint and registered with Microsoft Foundry as an OpenAPI tool.

For production, the service should be treated as an enterprise document-generation workload. It may process customer templates, prompts, generated presentation content, and downloadable artifacts. That means production hardening should focus on authentication, authorization, data storage, network exposure, content handling, monitoring, and lifecycle management.

Recommended production stance:

- Do not expose the Container App directly to broad public traffic without authentication.
- Put an enterprise access layer in front of the service.
- Store templates and generated artifacts in customer-controlled persistent storage.
- Limit what Foundry agents can call and which templates they can use.
- Add logging, alerting, auditability, and retention controls.
- Validate templates and generated artifacts before returning links to users.

## Current Prototype Posture

The baseline deployment is useful for demos and pilots because it is simple:

- Azure Container Apps hosts the API.
- External HTTPS ingress exposes the service.
- Azure Container Registry stores the image.
- A user-assigned managed identity pulls the image from ACR.
- Foundry calls the service through the OpenAPI document.
- Generated files are written to the container filesystem.

This is acceptable for a controlled demo or internal pilot, but production should add controls before handling sensitive documents or broad user traffic.

## Main Security Messages

Use these points when explaining the production path:

1. The generator should be treated as a data-processing API, not just a utility endpoint.
2. PowerPoint templates can contain brand assets, confidential structure, metadata, and customer-specific content.
3. Generated decks may contain sensitive strategy, financial, customer, or roadmap information.
4. The Foundry agent should be allowed to call only the operations it actually needs.
5. Public artifact URLs should not become permanent unauthenticated document links.
6. Production deployments need observability and audit trails for who generated what, when, and from which template.

## Recommended Production Controls

### 1. Authentication And Authorization

Production recommendation:

- Require authentication before any caller can use the API.
- Prefer Microsoft Entra ID based access for users, services, and agents.
- Put Azure API Management, Container Apps authentication, or an equivalent gateway in front of the service.
- Use managed identities where possible instead of secrets.

Talk track:

The prototype endpoint is easy for Foundry to call, but production should require a trusted identity at the boundary. The agent or gateway should prove who is calling, and the service should reject unauthenticated requests.

Questions to answer:

- Which identities are allowed to call the API?
- Will Foundry call through API Management, direct Container Apps authentication, or another gateway?
- Do different agents need different permissions?
- Should upload/onboard operations be restricted to administrators?

### 2. API Gateway And Policy Enforcement

Production recommendation:

- Use Azure API Management or an equivalent control plane for enterprise policies.
- Apply rate limits, request size limits, content-type checks, and authentication policies.
- Consider separate policies for generation, upload, validation, and artifact download.

Talk track:

An API gateway gives the security team a visible control point. It can enforce authentication, throttle abuse, limit payload sizes, log calls, and give Foundry a stable endpoint even if the backend changes.

Questions to answer:

- What maximum template upload size is allowed?
- How many deck generations per minute should be permitted?
- Should artifact downloads require signed URLs or authenticated access?
- Which operations should be exposed to agents versus administrators?

### 3. Network Exposure

Production recommendation:

- Avoid direct public ingress when policy requires private access.
- Consider internal Container Apps ingress, private endpoints, VNet integration, or API Management with private networking.
- Align the network path with the target Foundry project's network posture.

Talk track:

For a pilot, public HTTPS may be enough. For production, the network path should match enterprise policy. If the Foundry project is private or the data is sensitive, the generator should not be left as a broadly reachable public endpoint.

Questions to answer:

- Does the target Foundry project use public or private networking?
- Must the generator be reachable only from approved networks?
- Will API Management sit inside or outside the virtual network?

### 4. Persistent Storage For Templates And Artifacts

Production recommendation:

- Store templates and generated decks outside the container filesystem.
- Use Azure Blob Storage, SharePoint, OneDrive, or another customer-approved repository.
- Use managed identity for storage access.
- Apply retention, lifecycle management, and access controls.

Talk track:

Container filesystem storage is temporary and not an enterprise document repository. Production should store approved templates and generated decks in systems that support retention, access control, audit, and lifecycle policies.

Questions to answer:

- Where should approved templates live?
- Where should generated decks live?
- How long should generated decks be retained?
- Who can download generated decks?
- Should links expire?

### 5. Template Governance

Production recommendation:

- Maintain an approved template catalog.
- Restrict template upload/onboarding to trusted users or admins.
- Validate template file types and reject macro-enabled templates unless explicitly supported and reviewed.
- Track template version, owner, approval status, and intended use.

Talk track:

Templates are part of the trust boundary. They carry brand rules and may contain sensitive content. Production should not allow arbitrary templates to flow into the generator without validation and ownership.

Questions to answer:

- Who approves a template?
- How are template versions retired?
- Can agents upload templates, or only use approved templates?
- Is a separate review required for customer-specific templates?

### 6. Artifact Access And Link Safety

Production recommendation:

- Avoid permanent anonymous artifact URLs for sensitive decks.
- Use authenticated downloads, short-lived signed URLs, or storage-backed authorization.
- Log artifact access.
- Consider deleting generated artifacts after a defined retention period.

Talk track:

The user experience should make it easy to retrieve a deck, but artifact links are data access paths. In production, generated deck links should follow the same access policy as the content inside the deck.

Questions to answer:

- Are generated links public, authenticated, or time-limited?
- Can users share links outside the organization?
- Should artifact access be audited?
- What is the deletion policy?

### 7. Foundry Agent Tool Permissions

Production recommendation:

- Expose only the OpenAPI operations the agent needs.
- Use separate tools or policies for user-facing generation versus admin template management.
- Add clear agent instructions that prevent use of unapproved templates.
- Add evaluation cases for policy adherence.

Talk track:

The Foundry agent should not receive blanket access to every operation by default. Most user-facing agents need list, create, validate, and artifact retrieval. Template upload or onboarding should usually be a separate administrator path.

Suggested user-facing operations:

- `get_templates_api_templates_get`
- `post_create_deck_api_decks_create_post`
- `post_validate_deck_api_decks_validate_post`
- `get_artifact_api_artifacts__filename__get`

Admin-only candidates:

- `post_upload_template_api_templates_upload_post`
- `post_onboard_template_api_templates_onboard_post`
- `post_analyze_template_api_templates_analyze_post`

### 8. Input Validation And File Handling

Production recommendation:

- Enforce accepted file extensions and MIME types.
- Restrict file size.
- Sanitize filenames.
- Scan uploaded files if required by enterprise policy.
- Keep macro-enabled files disabled unless there is a reviewed business requirement.

Talk track:

PowerPoint files are complex packages. Production systems should handle them defensively, especially when users can upload templates.

Questions to answer:

- What file types are allowed?
- What is the maximum upload size?
- Are uploads malware-scanned?
- Are macros allowed or blocked?

### 9. Observability, Audit, And Incident Response

Production recommendation:

- Enable Container Apps logs and metrics.
- Track request IDs, template IDs, artifact IDs, validation results, and caller identity where policy allows.
- Send logs to a central workspace or SIEM.
- Create alerts for high error rates, high generation volume, failed validations, and suspicious upload behavior.

Talk track:

Security reviewers will want to know how the team can answer basic operational questions: who called the service, what was generated, which template was used, and whether validation passed.

Questions to answer:

- What logs are required for audit?
- How long are logs retained?
- Which events should alert operations or security?
- Who owns incident response for generated content issues?

### 10. Secret And Identity Management

Production recommendation:

- Keep ACR admin access disabled.
- Use managed identity for Azure resource access.
- Store any required secrets in Azure Key Vault.
- Avoid placing secrets in `.env` files, images, source code, or Foundry instructions.

Talk track:

The deployment should be identity-based wherever possible. If a secret is unavoidable, it should live in Key Vault and be injected into the runtime securely.

Questions to answer:

- Does the app need any secrets beyond Azure identity?
- Which identity can access storage?
- Which identity can pull from ACR?
- Who can rotate secrets or identities?

### 11. Data Classification And Retention

Production recommendation:

- Classify templates and generated decks according to enterprise policy.
- Apply retention and deletion rules.
- Decide whether generated content may be used for telemetry, evaluation, or model improvement.
- Avoid logging full prompt or document content unless approved.

Talk track:

Generated decks may be sensitive business records. Before production, the team should agree on whether the generated content is transient, retained, auditable, or subject to records management.

Questions to answer:

- What data classification applies to generated decks?
- Are prompts and deck plans logged?
- How long are artifacts retained?
- Are generated decks subject to eDiscovery or records retention?

## Suggested Production Roadmap

Phase 1: Controlled pilot

- Limit access to a small group.
- Keep public ingress only if policy allows.
- Use approved sample templates.
- Log requests and validation outcomes.
- Disable upload operations for user-facing agents unless needed.

Phase 2: Enterprise integration

- Put API Management or another access layer in front of the service.
- Add Microsoft Entra ID authentication.
- Move templates and artifacts to persistent controlled storage.
- Add signed or authenticated artifact downloads.
- Add operational dashboards and alerts.

Phase 3: Production readiness

- Add private networking if required.
- Complete threat modeling and security review.
- Define retention and audit policy.
- Add malware scanning or content inspection if required.
- Add Foundry evaluations for policy adherence, content quality, and template fidelity.
- Document operational ownership and incident response.

## Stakeholder Talk Track

Use this short version in meetings:

```text
The current deployment gives Foundry agents a working PowerPoint generation tool through OpenAPI. For production, we should treat it as a document-generation API that handles potentially sensitive templates and generated decks. Before broad rollout, we recommend adding an authenticated access layer, restricting agent operations to least privilege, storing templates and artifacts in customer-controlled persistent storage, using managed identities and Key Vault for secrets, and adding logging, alerting, retention, and audit controls. Template upload and onboarding should usually be admin-only. Artifact links should be authenticated or time-limited rather than permanent public URLs.
```

## Decisions To Capture Before Production

Capture these decisions before a production launch:

- Authentication mechanism
- Network exposure model
- API gateway choice
- Template storage location
- Generated artifact storage location
- Artifact link expiration and access policy
- Allowed Foundry tool operations
- Upload/onboarding ownership
- Logging and audit requirements
- Retention and deletion policy
- Incident response owner
- Production support owner
