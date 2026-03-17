from __future__ import annotations

ACTION_REGISTRY: dict[str, dict] = {
    "list_vms": {
        "description": "List all virtual machines in the environment.",
        "params": {},
    },
    "create_vm": {
        "description": "Create a new virtual machine.",
        "params": {
            "name": "string (required) - VM name",
            "cpu": "integer (optional, default 2) - number of vCPUs",
            "memory_mb": "integer (optional, default 4096) - memory in MB",
            "disk_gb": "integer (optional, default 40) - disk size in GB",
        },
    },
    "insight": {
        "description": "Answer a question about the infrastructure state, capacity, health, or performance.",
        "params": {
            "question": "string (required) - the user's question",
        },
    },
}


def _format_actions() -> str:
    lines: list[str] = []
    for name, info in ACTION_REGISTRY.items():
        lines.append(f"- {name}: {info['description']}")
        if info["params"]:
            for pname, pdesc in info["params"].items():
                lines.append(f"    {pname}: {pdesc}")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""\
You are vWrapper, an AI assistant that controls VMware infrastructure.

Your job is to interpret the user's natural language command and return a \
structured JSON action.

Available actions:
{_format_actions()}

Rules:
- Return ONLY valid JSON, no markdown, no explanation.
- Pick the single best matching action.
- If the user is asking a question about their environment (health, capacity, \
performance, what's wrong, etc.), use the "insight" action.
- If the intent is unclear, default to "insight" with the user's query as the question.
- For create_vm, infer reasonable defaults if not specified. Generate a sensible \
name from context (e.g., "dev-vm-1").

Response format:
{{"action": "<action_name>", "params": {{...}}}}
"""
