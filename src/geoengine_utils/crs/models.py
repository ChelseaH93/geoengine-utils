from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class CRSInfo:
    auth_name: str
    code: str
    name: str
    area_of_use: str


@dataclass(slots=True)
class CRSRecommendation:
    recommended: CRSInfo
    alternatives: List[CRSInfo]
    reason: str