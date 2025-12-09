from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class Skill:
    skill_id: str
    name: str
    source_span: tuple[int, int]


@dataclass
class Series:
    series_id: str
    skill_id: str
    label: str
    units: str
    meta: Dict[str, Any]


@dataclass
class ValuePoint:
    id: Optional[int]
    series_id: str
    level_index: int
    value: float
    diff_to_prev: Optional[float]
    is_jump: bool


@dataclass
class Analysis:
    series_id: str
    is_linear: bool
    trend: str
    min: Optional[float]
    max: Optional[float]
    count: int
    jump_points: List[int]

