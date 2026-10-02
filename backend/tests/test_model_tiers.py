"""Model classification tests (v1.0.2 parameter-count rules)."""

from __future__ import annotations

import pytest
from app.services.models.service import (
    TIER_HIGH,
    TIER_MEDIUM,
    TIER_POTATO,
    parse_parameter_billions,
    tier_for_parameters,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.5B", 1.5),
        ("3B", 3.0),
        ("7.6b", 7.6),
        ("70B", 70.0),
        ("8x7B", 56.0),
        (None, None),
        ("unknown", None),
    ],
)
def test_parse_parameter_billions(raw, expected):
    assert parse_parameter_billions(raw) == expected


@pytest.mark.parametrize(
    ("raw", "tier"),
    [
        ("0.5B", TIER_POTATO),
        ("1.5B", TIER_POTATO),
        ("2.9B", TIER_POTATO),
        ("3B", TIER_MEDIUM),
        ("7B", TIER_MEDIUM),
        ("7.9B", TIER_MEDIUM),
        ("8B", TIER_HIGH),
        ("32B", TIER_HIGH),
        ("70B", TIER_HIGH),
        (None, TIER_MEDIUM),
    ],
)
def test_tier_for_parameters(raw, tier):
    assert tier_for_parameters(raw) == tier
