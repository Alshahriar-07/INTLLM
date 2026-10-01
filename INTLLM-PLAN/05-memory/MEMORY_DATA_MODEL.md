# Memory Data Model

## memory_items

Suggested fields:

- id UUID
- type enum: fact/workflow/failure
- title
- content
- normalized_content
- confidence
- importance
- created_at
- updated_at
- verified_at
- expires_at
- status

## memory_sources

- memory_id
- url
- title
- source_type
- retrieved_at
- published_at if known
- verification_status

## flash_index

- memory_id
- embedding vector
- keywords
- memory_type
- confidence
- expires_at
- last_accessed_at
- access_count

## Rules

Never blindly overwrite a high-confidence memory with one unverified source. Create a candidate/update record, compare evidence, then promote.
