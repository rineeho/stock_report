"""Brokerage name normalizer: maps variant names to canonical form."""

from __future__ import annotations

# Canonical name → list of variant names (including canonical itself)
_BROKERAGE_MAP: dict[str, list[str]] = {
    "미래에셋증권": ["미래에셋증권", "미래에셋대우", "미래에셋대우증권"],
    "메리츠증권": ["메리츠증권", "메리츠종금증권", "메리츠종금"],
    "하나증권": ["하나증권", "하나금융투자"],
    "신한투자증권": ["신한투자증권", "신한금융투자", "신한금융투자증권"],
    "한국투자증권": ["한국투자증권", "한투증권"],
    "NH투자증권": ["NH투자증권", "NH증권", "농협증권"],
    "KB증권": ["KB증권", "KB투자증권", "현대증권"],
    "삼성증권": ["삼성증권"],
    "키움증권": ["키움증권"],
    "대신증권": ["대신증권"],
    "IBK투자증권": ["IBK투자증권", "IBK증권"],
    "SK증권": ["SK증권"],
    "교보증권": ["교보증권"],
    "유진투자증권": ["유진투자증권", "유진증권"],
    "유안타증권": ["유안타증권"],
    "흥국증권": ["흥국증권"],
    "BNK투자증권": ["BNK투자증권"],
    "iM증권": ["iM증권", "DGB금융투자"],
    "현대차증권": ["현대차증권"],
    "LS증권": ["LS증권"],
}

# Build reverse lookup: variant → canonical
_REVERSE_MAP: dict[str, str] = {}
for canonical, variants in _BROKERAGE_MAP.items():
    for variant in variants:
        _REVERSE_MAP[variant] = canonical


def normalize_brokerage(raw_name: str) -> str:
    """Normalize a brokerage name to its canonical form.

    Returns the raw_name unchanged if no mapping exists.
    """
    if not raw_name:
        return raw_name
    return _REVERSE_MAP.get(raw_name.strip(), raw_name.strip())
