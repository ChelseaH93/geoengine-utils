from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class CRSInfo:
    auth_name: str
    code: str
    name: str
    area_of_use: Optional[str] = None
    score: int = 0


@dataclass(slots=True)
class CRSRecommendation:
    recommended: CRSInfo
    alternatives: list[CRSInfo]
    reason: str