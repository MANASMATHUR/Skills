import argparse
import sys
import yaml
from datetime import datetime, timezone
from datastore import DataStore

store = DataStore()

def get_iso_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def list_clients(args):
    clients = store.list_clients()
    if not clients:
        print("No clients registered in .fde-memory.")
        return
    print(yaml.dump({"clients": clients}, default_flow_style=False))

def init_client(args):
    client_name = args.client.strip()
    if store.client_exists(client_name) and not args.force:
        print(f"Error: Client '{client_name}' already exists. Use --force to overwrite baseline profile.")
        sys.exit(1)

    template = {
        "client_name": client_name,
        "infrastructure": args.infrastructure or "Not specified",
        "auth": args.auth or "Not specified",
        "data_residency": args.data_residency or "Not specified",
        "deployment_model": args.deployment_model or "Not specified",
        "notes": args.notes or "",
        "created_at": get_iso_timestamp(),
        "decisions": []
    }
    store.write_client(client_name, template)
    print(f"Successfully initialized client profile for '{client_name}'.")

def set_context(args):
    if not store.client_exists(args.client):
        print(f"Error: Client '{args.client}' does not exist. Initialize first using 'init-client'.")
        sys.exit(1)

    key_value_pairs = [pair.strip() for pair in args.set.split(';') if pair.strip()]
    updates = {}
    for pair in key_value_pairs:
        if '=' not in pair:
            print(f"Error: Invalid key-value format '{pair}'. Expected format: key=value")
            sys.exit(1)
        k, v = pair.split('=', 1)
        updates[k.strip()] = v.strip()

    if not updates:
        print("Error: No key-value pairs provided to update.")
        sys.exit(1)

    store.update_client_keys(args.client, updates)
    print(f"Successfully updated context for client '{args.client}'.")

def get_context(args):
    data = store.read_client(args.client)
    if not data:
        print(f"Error: Client '{args.client}' not found in datastore.")
        sys.exit(1)

    if args.keys:
        keys = [k.strip() for k in args.keys.split(',') if k.strip()]
        extracted = {k: data.get(k, "Not defined") for k in keys}
        print(yaml.dump(extracted, default_flow_style=False))
    else:
        # Return all metadata keys excluding the long decision audit trail unless explicitly asked
        summary = {k: v for k, v in data.items() if k != "decisions"}
        summary["decision_count"] = len(data.get("decisions", []))
        print(yaml.dump(summary, default_flow_style=False))

def check_conflict(args):
    data = store.read_client(args.client)
    if not data:
        print(f"Error: Client '{args.client}' does not exist.")
        sys.exit(1)

    component_query = args.component.strip().lower()
    decisions = data.get("decisions", [])
    matching_decisions = [
        d for d in decisions if d.get("component", "").strip().lower() == component_query
    ]

    # Also inspect top-level fields for direct architectural constraints
    direct_value = data.get(component_query)

    result = {
        "client": args.client,
        "component": args.component,
        "top_level_constraint": direct_value if direct_value else "None",
        "has_prior_decisions": len(matching_decisions) > 0,
        "prior_decisions": matching_decisions
    }

    print(yaml.dump(result, default_flow_style=False))

def log_decision(args):
    data = store.read_client(args.client)
    if not data:
        print(f"Error: Client '{args.client}' does not exist. Initialize first using 'init-client'.")
        sys.exit(1)

    component = args.component.strip()
    decision = args.decision.strip()
    justification = args.justification.strip()

    if not justification or len(justification) < 5:
        print("Error: A non-empty justification is mandatory when recording an architectural decision.")
        sys.exit(1)

    decisions = data.get("decisions", [])
    
    # Conflict guardrail: check if a prior decision for this component exists
    prior = [d for d in decisions if d.get("component", "").strip().lower() == component.lower()]
    if prior and not args.force:
        latest = prior[-1]
        print("CONFLICT_DETECTED")
        print(f"Prior decision recorded for component '{component}':")
        print(f"  Decision: {latest.get('decision')}")
        print(f"  Justification: {latest.get('justification')}")
        print(f"  Timestamp: {latest.get('timestamp')}")
        print("\nAction blocked: To record a replacement decision, provide explicit rationale and pass --force.")
        sys.exit(2)

    new_decision = {
        "timestamp": get_iso_timestamp(),
        "component": component,
        "decision": decision,
        "justification": justification,
        "is_override": len(prior) > 0
    }
    decisions.append(new_decision)
    data["decisions"] = decisions

    # Keep top-level component attribute synchronized if applicable
    if component.lower() in data:
        data[component.lower()] = decision

    store.write_client(args.client, data)
    print(f"Successfully recorded decision for client '{args.client}': {component} -> {decision}")

def generate_handoff(args):
    data = store.read_client(args.client)
    if not data:
        print(f"Error: Client '{args.client}' does not exist.")
        sys.exit(1)

    client_title = data.get("client_name", args.client).upper()
    infra = data.get("infrastructure", "Not specified")
    auth = data.get("auth", "Not specified")
    data_residency = data.get("data_residency", "Not specified")
    deployment = data.get("deployment_model", "Not specified")
    decisions = data.get("decisions", [])

    markdown = f"""# FDE Context Handoff: {client_title}
Generated: {get_iso_timestamp()}

## Human Summary
- Infrastructure: {infra}
- Authentication: {auth}
- Data Residency: {data_residency}
- Deployment Model: {deployment}
- Total Architectural Decisions: {len(decisions)}

## Decision Audit Log
"""
    if decisions:
        for idx, d in enumerate(decisions, start=1):
            override_flag = " [OVERRIDE]" if d.get("is_override") else ""
            markdown += f"{idx}. **{d.get('component')}**: `{d.get('decision')}`{override_flag}\n"
            markdown += f"   - Justification: {d.get('justification')}\n"
            markdown += f"   - Date: {d.get('timestamp')}\n"
    else:
        markdown += "No explicit decision records logged.\n"

    markdown += f"""
## Machine State Specification
```yaml
{yaml.dump(data, default_flow_style=False)}
```
"""
    print(markdown)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FDE FieldOps Memory Core CLI")
    subparsers = parser.add_subparsers(dest="command")

    # List Clients
    subparsers.add_parser("list-clients", help="List all tracked client profiles")

    # Init Client
    p_init = subparsers.add_parser("init-client", help="Initialize a new client profile")
    p_init.add_argument("--client", required=True, help="Client identifier or name")
    p_init.add_argument("--infrastructure", help="Cloud or host infrastructure constraints")
    p_init.add_argument("--auth", help="Auth/SSO requirements")
    p_init.add_argument("--data-residency", help="Data residency regulations")
    p_init.add_argument("--deployment-model", help="SaaS, On-Prem, VPC Peering, etc.")
    p_init.add_argument("--notes", help="Initial scope notes")
    p_init.add_argument("--force", action="store_true", help="Force overwrite existing client profile")

    # Set Context
    p_set = subparsers.add_parser("set-context", help="Update client metadata fields")
    p_set.add_argument("--client", required=True, help="Client identifier")
    p_set.add_argument("--set", required=True, help="Semicolon-delimited key=value pairs (e.g. auth=Okta;vpc=isolated)")

    # Get Context
    p_get = subparsers.add_parser("get-context", help="Targeted context retrieval")
    p_get.add_argument("--client", required=True, help="Client identifier")
    p_get.add_argument("--keys", help="Comma-separated keys to extract (e.g. auth,infrastructure)")

    # Check Conflict
    p_chk = subparsers.add_parser("check-conflict", help="Inspect prior decisions for architectural conflict")
    p_chk.add_argument("--client", required=True, help="Client identifier")
    p_chk.add_argument("--component", required=True, help="Component or architecture element to check")

    # Log Decision
    p_log = subparsers.add_parser("log-decision", help="Record architectural decision or approved override")
    p_log.add_argument("--client", required=True, help="Client identifier")
    p_log.add_argument("--component", required=True, help="Architectural component")
    p_log.add_argument("--decision", required=True, help="Chosen implementation or architecture")
    p_log.add_argument("--justification", required=True, help="Mandatory business/technical justification")
    p_log.add_argument("--force", action="store_true", help="Confirm override if prior decision exists")

    # Generate Handoff
    p_hand = subparsers.add_parser("generate-handoff", help="Generate dual human/machine handoff package")
    p_hand.add_argument("--client", required=True, help="Client identifier")

    args = parser.parse_args()

    dispatch = {
        "list-clients": list_clients,
        "init-client": init_client,
        "set-context": set_context,
        "get-context": get_context,
        "check-conflict": check_conflict,
        "log-decision": log_decision,
        "generate-handoff": generate_handoff,
    }

    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()
