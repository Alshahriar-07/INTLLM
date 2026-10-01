# Tool Gateway

Models never directly execute OS/browser operations.

## Tool flow

```text
Model tool request
 -> schema validation
 -> policy check
 -> permission
 -> execution
 -> result sanitization
 -> model
```

## Initial tools

### Read-only

- web.search
- web.open
- web.extract
- browser.open
- browser.read
- browser.screenshot
- brain.search
- system.info

### Controlled actions

- browser.click
- browser.type
- browser.navigate
- filesystem.read
- filesystem.write
- terminal.execute

Controlled actions need explicit policy and, where appropriate, user approval.

## Tool schema

Every tool defines:

- name
- version
- description
- JSON schema
- risk level
- timeout
- permissions
- audit policy
