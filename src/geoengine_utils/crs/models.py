"""Data models for CRS recommendations."""

from dataclasses import dataclass


@dataclass(slots=True)
class CRSInfo:
    """Structured information about a CRS candidate."""

    auth_name: str
    code: str
    name: str
    area_of_use: str | None
    score: float = 0


@dataclass(slots=True)
class CRSRecommendation:
    """A recommended CRS plus ranked alternatives and rationale."""

    recommended: CRSInfo
    alternatives: list[CRSInfo]
    reason: str