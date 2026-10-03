"""Background learning: low-priority maintenance that yields to user requests."""

from app.services.background.governor import ResourceGovernor, ResourceState
from app.services.background.service import BackgroundLearningService, get_background_service

__all__ = [
    "BackgroundLearningService",
    "ResourceGovernor",
    "ResourceState",
    "get_background_service",
]
