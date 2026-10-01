# Hardware Detection

Detect locally:

- OS
- CPU model/core count
- RAM
- GPU model
- VRAM
- disk free space
- architecture
- Ollama availability
- installed models

## Tier recommendation

Potato:
- prioritize small quantized models
- low memory usage
- smaller context

Nutral:
- balanced 7B/14B-class options where hardware permits
- moderate context

I Paid for My Whole PC:
- larger models
- larger context
- heavier agent workflows

Do not hardcode a single model per tier. Use a registry and compatibility score.
