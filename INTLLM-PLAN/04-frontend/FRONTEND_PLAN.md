# Frontend Plan

## Stack

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- TanStack Query for server state
- Zustand or equivalent for small client state

## Main layout

```text
Sidebar
  Chat
  Models
  Brain
  Browser
  Tools
  API
  System
  Settings

Main workspace
  Header
  Context/status bar
  Content
  Composer

Optional right panel
  Memory / sources / tool activity
```

## Chat requirements

- streaming tokens
- markdown
- code blocks
- copy buttons
- source cards
- tool activity
- memory-used indicator
- stop generation
- regenerate
- conversation search
- model selector

## System status

Show:

- Ollama status
- model
- PostgreSQL status
- Flash Brain status
- Internet/retrieval status
- browser status
- background learner status
- CPU/RAM/GPU usage

## UX principle

Do not expose internal complexity unless useful. The user should see a simple AI interface while INTLLM handles orchestration underneath.
