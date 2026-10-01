# Product Specification

## Product statement

INTLLM is a local-first AI environment that wraps local language models with live information retrieval, memory, tools, browser capabilities and an OpenAI-compatible API.

## User journey

1. User runs `intllm`.
2. INTLLM checks OS, CPU, RAM, GPU/VRAM, disk, PostgreSQL and Ollama.
3. Missing dependencies are handled through a guided local setup.
4. INTLLM recommends compatible models.
5. User selects or installs a model.
6. Browser opens the local portal.
7. User can immediately chat.
8. INTLLM checks Flash Brain before expensive retrieval.
9. If memory is missing/stale and the task requires current information, the retrieval layer is used.
10. Validated reusable knowledge is compacted into memory.
11. Background maintenance continues at low priority when resources are available.

## Hardware tiers

Use the exact product labels:

- Potato — low-end/iGPU/older hardware.
- Nutral — balanced/mid-range hardware.
- I Paid for My Whole PC — high-end hardware.

These are recommendations, not hard restrictions.

## Product surfaces

- Chat
- Model Manager
- Brain / Memory
- Web & Browser
- Tools
- API Keys
- API Playground
- System Monitor
- Settings
- Logs / Diagnostics
- Background Learning status

## Non-goals for v1

- Full base-model continual weight training.
- Autonomous unrestricted browser actions.
- Cloud-first storage.
- Automatic destructive OS actions.
- Saving every raw webpage permanently.
