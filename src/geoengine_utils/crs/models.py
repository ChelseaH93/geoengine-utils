from dataclasses import dataclass


@dataclass(slots=True)
class CRSInfo:
    auth_name: str
    code: str
    name: str
    area_of_use: str


@dataclass(slots=True)
class CRSRecommendation:
    recommended: CRSInfo
    alternatives: list[CRSInfo]
    reason: str