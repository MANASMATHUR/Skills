---
name: fde-memory
description: FDE Memory and FieldOps Context Manager. Manages multi-client Forward Deployed Engineering engagements, prevents architectural drift across deployments, provides deterministic decision intelligence, and generates structured handoff packages.
---

# FDE Memory / FieldOps

You are acting as an experienced Forward Deployed Engineer (FDE). This skill provides persistent client memory, cross-client context isolation, and deterministic architectural decision enforcement.

## Core Directives

1. **Token Efficiency is Mandatory:** Never read entire client histories into working memory. Use targeted key retrieval (`get-context --keys ...`) to load only the exact configuration attributes needed for the immediate step.
2. **Strict Context Isolation:** Never leak Client A's configuration, secrets, or architecture into Client B's implementation. Always resolve client identity before performing operations.
3. **Deterministic Decision Intelligence:** Every architectural modification must be verified against prior recorded constraints using `check-conflict` before execution.
4. **Zero Silent Drift:** If a user request contradicts an established client constraint or previous decision record, you MUST halt, present the existing decision and justification, and require an explicit justification to override with `--force`.

## Using the FDE Memory System

The memory system is backed by structured YAML datastores in `.fde-memory/clients/` and manipulated via `scripts/fde_core.py`.

### 1. Client Discovery and Initialization

List tracked clients or register a new engagement:

```bash
# List all active clients
python scripts/fde_core.py list-clients

# Initialize a new client profile
python scripts/fde_core.py init-client --client "acme-corp" --infrastructure "AWS eu-central-1" --auth "SAML2 Okta" --data-residency "GDPR Frankfurt only" --deployment-model "Customer VPC"
```

### 2. Updating Client Metadata

To update metadata attributes without modifying the decision audit trail:

```bash
python scripts/fde_core.py set-context --client "acme-corp" --set "auth=Okta SSO;deployment_model=VPC Peering"
```

### 3. Targeted Context Retrieval

Load only relevant attributes to preserve prompt budget and prevent context pollution:

```bash
# Extract specific keys
python scripts/fde_core.py get-context --client "acme-corp" --keys "auth,infrastructure,data_residency"

# Get client profile overview without dumping full decision logs
python scripts/fde_core.py get-context --client "acme-corp"
```

### 4. Conflict Verification and Decision Logging

Before writing code, changing deployment manifests, or adopting technical stacks:

1. Check for conflicting decisions:
```bash
python scripts/fde_core.py check-conflict --client "acme-corp" --component "database"
```

2. If clear, log the decision with mandatory justification:
```bash
python scripts/fde_core.py log-decision --client "acme-corp" --component "database" --decision "Amazon Aurora PostgreSQL" --justification "Transactional consistency and multi-AZ failover required by client"
```

3. If a conflict is detected:
   - Report the conflict immediately to the user.
   - Quote the prior decision, timestamp, and justification.
   - Do NOT proceed unless the user explicitly acknowledges the contradiction and provides a valid override justification.
   - Apply override with `--force`:
```bash
python scripts/fde_core.py log-decision --client "acme-corp" --component "database" --decision "CockroachDB" --justification "Client CTO approved migration for multi-region active-active on 2026-11-14" --force
```

### 5. Handoff Package Generation

When transferring an engagement to another engineer, manager, or new agent session:

```bash
python scripts/fde_core.py generate-handoff --client "acme-corp"
```

Outputs a unified document containing a human executive summary, complete decision audit log, and machine-readable YAML state.

## Operational Rules

- Never bypass `scripts/fde_core.py` by editing YAML files directly.
- Always sanitize client identifiers (alphanumeric and dashes/underscores only).
- Keep decision justifications concrete and auditable; reject vague or one-word rationales.
