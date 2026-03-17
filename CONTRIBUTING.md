# Contributing to vWrapper

Thanks for your interest in contributing! vWrapper is an early-stage project and we welcome all kinds of contributions.

## Getting Started

```bash
git clone https://github.com/patelpa1639/vwrapper.git
cd vwrapper
pip install -e ".[dev]"
```

## What We're Looking For

- **New actions** — `power_on`, `power_off`, `snapshot`, `clone`, etc.
- **New providers** — Proxmox, libvirt, AWS EC2, Azure VMs
- **Better guardrails** — more safety rules, RBAC, audit logging
- **Tests** — unit tests, integration tests, mocks for pyvmomi
- **Docs** — usage examples, tutorials, architecture docs
- **Bug fixes** — always welcome

## Development Workflow

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Open a PR against `main`

## Code Style

- Python 3.11+
- Type hints everywhere
- `from __future__ import annotations` at the top of every module
- Pydantic for data models
- Rich for terminal output

## Adding a New Action

1. Add the action to the registry in `src/vwrapper/agent/prompts.py`
2. Implement it in `src/vwrapper/providers/vmware.py`
3. Add the execution branch in `src/vwrapper/cli.py`
4. Add guardrail rules in `src/vwrapper/guardrails/rules.py`
5. Write tests

## Adding a New Provider

Providers live in `src/vwrapper/providers/`. Follow the pattern in `vmware.py`:

- A class with `connect()`, `disconnect()`, `list_vms()`, `create_vm()`, etc.
- Context manager support (`__enter__` / `__exit__`)
- Return `ActionResult` and `VMInfo` models

## Commit Messages

Keep them short and descriptive. Examples:

- `feat: add power_on/power_off actions`
- `fix: handle disconnected vCenter gracefully`
- `docs: add proxmox provider example`

## Questions?

Open an issue — we're happy to help.
