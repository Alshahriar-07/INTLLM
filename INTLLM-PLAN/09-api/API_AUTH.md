# Local API Authentication

Users can create API keys from the INTLLM web portal.

Example:

```text
Authorization: Bearer intllm_...
```

Requirements:

- random high-entropy key
- hash at rest
- creation timestamp
- last-used timestamp
- optional scopes
- revoke support
- audit events
- never log the raw key

Default server should bind to localhost.

LAN exposure must be an explicit opt-in with warning and access controls.
