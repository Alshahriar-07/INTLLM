"""Ollama lifecycle control (process/service management).

This package owns the *process* lifecycle of the local Ollama daemon. HTTP
conversation with a running daemon stays in
``app.services.runtime.ollama`` (the model adapter); route handlers never
spawn or kill processes directly.
"""
