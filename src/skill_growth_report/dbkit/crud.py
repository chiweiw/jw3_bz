from typing import Iterable, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Skill, Series, Value, Analysis


def upsert_skill(session: Session, skill_id: str, name: str, source_span: str) -> None:
    obj = session.execute(select(Skill).where(Skill.skill_id == skill_id)).scalar_one_or_none()
    if obj is None:
        obj = Skill(skill_id=skill_id, name=name, source_span=source_span)
        session.add(obj)
    else:
        obj.name = name
        obj.source_span = source_span


def upsert_series(session: Session, series_id: str, skill_id: str, label: str, units: str, meta_json: str) -> None:
    obj = session.execute(select(Series).where(Series.series_id == series_id)).scalar_one_or_none()
    if obj is None:
        obj = Series(series_id=series_id, skill_id=skill_id, label=label, units=units, meta=meta_json)
        session.add(obj)
    else:
        obj.skill_id = skill_id
        obj.label = label
        obj.units = units
        obj.meta = meta_json


def replace_values(session: Session, series_id: str, rows: Iterable[Dict[str, Any]]) -> None:
    session.query(Value).filter(Value.series_id == series_id).delete()
    for r in rows:
        session.add(
            Value(
                series_id=series_id,
                level_index=r["level_index"],
                value=r["value"],
                diff_to_prev=r.get("diff_to_prev"),
                is_jump=1 if r.get("is_jump") else 0,
            )
        )


def upsert_analysis(session: Session, series_id: str, a: Dict[str, Any], jump_points_json: str) -> None:
    obj = session.execute(select(Analysis).where(Analysis.series_id == series_id)).scalar_one_or_none()
    is_linear = 1 if a.get("is_linear") else 0
    trend = a.get("trend") or "mixed"
    min_v = a.get("min")
    max_v = a.get("max")
    count_v = a.get("count") or 0
    if obj is None:
        obj = Analysis(series_id=series_id, is_linear=is_linear, trend=trend, min=min_v, max=max_v, count=count_v, jump_points=jump_points_json)
        session.add(obj)
    else:
        obj.is_linear = is_linear
        obj.trend = trend
        obj.min = min_v
        obj.max = max_v
        obj.count = count_v
        obj.jump_points = jump_points_json
