<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-Apache--2.0-green" alt="License">
  <img src="https://img.shields.io/badge/version-0.1.0-orange" alt="Version">
  <img src="https://img.shields.io/badge/LLM-Claude%20%7C%20OpenAI-purple" alt="LLM Support">
</p>

<h1 align="center">vWrapper</h1>

<p align="center">
  <strong>Talk to your VMware infrastructure in plain English.</strong><br>
  An AI-powered CLI that translates natural language into VMware vCenter operations — with built-in guardrails.
</p>

<p align="center">
  <code>vwrapper "spin up a 4-cpu dev box called test-api"</code>
</p>

---

## What is this?

vWrapper is like [Claude Code](https://docs.anthropic.com/en/docs/claude-code) or [OpenAI Codex CLI](https://github.com/openai/codex) — but for infrastructure.

Instead of writing code, you manage VMs. Instead of a repo, your workspace is a vCenter cluster.

```
$ vwrapper "list all my VMs"

  🧠 Parsing intent...
  🔌 Connecting to vCenter...
  🔒 Validating...
  ⚙️  Executing...

┌─────────────────────────────────────────────────────┐
│                  Virtual Machines                     │
├──────────┬─────────┬─────┬────────────┬─────────────┤
│ Name     │ Power   │ CPU │ Memory (MB)│ IP Address  │
├──────────┼─────────┼─────┼────────────┼─────────────┤
│ web-01   │ On      │   4 │       8192 │ 10.0.1.10   │
│ db-01    │ On      │   8 │      16384 │ 10.0.1.20   │
│ dev-box  │ Off     │   2 │       4096 │ -           │
└──────────┴─────────┴─────┴────────────┴─────────────┘
```

## Features

- **Natural language** — just describe what you want in plain English
- **AI-powered intent parsing** — uses Claude or GPT to understand your request
- **Guardrails** — destructive actions are blocked, dangerous ones require confirmation
- **Dry-run mode** — see what would happen before it happens
- **Infrastructure insights** — ask questions about capacity, health, and performance
- **Rich terminal UI** — colored output, tables, and panels via [Rich](https://github.com/Textualize/rich)

## Quick Start

### Install

```bash
pip install vwrapper
```

Or from source:

```bash
git clone https://github.com/patelpa1639/vwrapper.git
cd vwrapper
pip install -e .
```

### Configure

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

```env
# vCenter connection
VCENTER_HOST=vcenter.lab.local
VCENTER_USER=administrator@vsphere.local
VCENTER_PASSWORD=your-password

# LLM provider: "anthropic" or "openai"
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...
```

### Use

```bash
# List VMs
vwrapper "show me all VMs"

# Create a VM
vwrapper "create a VM called web-02 with 4 CPUs and 8GB RAM"

# Ask about your infrastructure
vwrapper "is my cluster running hot?"

# Dry run — see what would happen
vwrapper "create a big VM for the ML team" --dry-run

# Skip confirmation prompts
vwrapper "spin up a dev box" --yes

# Check vCenter connectivity
vwrapper status
```

## How It Works

```
  You: "spin up a 4-cpu dev box called test-api"
   │
   ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  LLM Intent  │ ──▶ │  Guardrails  │ ──▶ │   vCenter    │
│   Parsing    │     │  Validation  │     │  Execution   │
└──────────────┘     └──────────────┘     └──────────────┘
   │                    │                    │
   │ Extracts:          │ Checks:            │ Runs:
   │ action: create_vm  │ ✓ Not destructive  │ CreateVM_Task
   │ name: test-api     │ ✓ Under VM limit   │
   │ cpu: 4             │ ✓ User confirmed   │
   └────────────────────┴────────────────────┘
```

1. **Parse** — Your natural language query is sent to an LLM (Claude or GPT) which extracts a structured action
2. **Validate** — Guardrails check the action against safety rules (destructive action blocking, VM limits, confirmation requirements)
3. **Execute** — The validated action is executed against vCenter via the pyvmomi SDK

## Guardrails

vWrapper ships with safety-first defaults:

| Rule | Behavior |
|---|---|
| Destructive actions (`delete_vm`, `destroy_vm`, `reset_vm`, `format_datastore`) | **Blocked** — always |
| VM creation | **Requires confirmation** (bypass with `--yes`) |
| VM limit | **Blocked** when `VWRAPPER_MAX_VMS` is reached |
| Dry-run mode | **Blocks all execution** — shows what would happen |

## Supported Actions

| Action | Description |
|---|---|
| `list_vms` | List all VMs in the environment |
| `create_vm` | Create a new VM with specified resources |
| `insight` | Ask questions about infrastructure health, capacity, performance |

More actions coming soon — PRs welcome!

## Configuration

All config is via environment variables (or a `.env` file):

| Variable | Default | Description |
|---|---|---|
| `VCENTER_HOST` | `vcenter.lab.local` | vCenter hostname |
| `VCENTER_USER` | `administrator@vsphere.local` | vCenter username |
| `VCENTER_PASSWORD` | — | vCenter password |
| `VCENTER_INSECURE` | `true` | Skip TLS verification |
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `LLM_API_KEY` | — | API key for your LLM provider |
| `LLM_MODEL` | `claude-haiku-4-5-20251001` | Model to use |
| `VWRAPPER_MAX_VMS` | `50` | Maximum VMs allowed |
| `VWRAPPER_DRY_RUN` | `false` | Enable dry-run mode globally |

## Project Structure

```
src/vwrapper/
├── cli.py              # Typer CLI entrypoint
├── config.py           # Pydantic settings & env loading
├── output.py           # Rich terminal output (tables, panels)
├── agent/
│   ├── intent.py       # LLM-powered intent parsing
│   └── prompts.py      # System prompts & action registry
├── guardrails/
│   └── rules.py        # Safety validation rules
├── models/
│   └── actions.py      # Pydantic models (Action, VMInfo, etc.)
└── providers/
    └── vmware.py       # pyvmomi vCenter provider
```

## Development

```bash
git clone https://github.com/patelpa1639/vwrapper.git
cd vwrapper
pip install -e ".[dev]"
pytest
```

## Roadmap

- [ ] `power_on` / `power_off` / `restart` VM actions
- [ ] Snapshot management
- [ ] Multi-cluster support
- [ ] Interactive mode (REPL)
- [ ] Plugin system for custom providers
- [ ] MCP server integration

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[Apache 2.0](LICENSE) — use it however you want.
