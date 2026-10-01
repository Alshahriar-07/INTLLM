# Model Registry

Each model entry should define:

- name
- Ollama identifier
- family
- parameters
- quantization
- context length
- approximate RAM/VRAM requirement
- recommended tier
- tool calling capability
- structured output capability
- license
- download size
- source URL
- verification timestamp

## Install flow

```text
Detect
 -> recommend
 -> user selects
 -> disk check
 -> pull
 -> verify
 -> smoke test
 -> register
 -> ready
```

Avoid claiming a model is "best". Use compatibility/relevance signals instead.
