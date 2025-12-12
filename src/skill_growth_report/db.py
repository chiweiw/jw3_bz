from typing import Iterable, Dict, Any
from pathlib import Path
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, ForeignKey, Index
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()


class Skill(Base):
    __tablename__ = "skills"
    skill_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    source_span = Column(Text, nullable=False)


class Series(Base):
    __tablename__ = "series"
    series_id = Column(String, primary_key=True)
    skill_id = Column(String, ForeignKey("skills.skill_id"), nullable=False)
    label = Column(String, nullable=False)
    units = Column(String, nullable=False)
    meta = Column(Text)


class Value(Base):
    __tablename__ = "values_tbl"
    id = Column(Integer, primary_key=True, autoincrement=True)
    series_id = Column(String, ForeignKey("series.series_id"), nullable=False)
    level_index = Column(Integer, nullable=False)
    value = Column(Float, nullable=False)
    diff_to_prev = Column(Float)
    is_jump = Column(Integer, nullable=False)


Index("idx_values_series_level", Value.series_id, Value.level_index)


class Analysis(Base):
    __tablename__ = "analysis"
    series_id = Column(String, ForeignKey("series.series_id"), primary_key=True)
    is_linear = Column(Integer, nullable=False)
    trend = Column(Text, nullable=False)
    min = Column(Float)
    max = Column(Float)
    count = Column(Integer, nullable=False)
    jump_points = Column(Text, nullable=False)


def get_session(db_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    return SessionLocal()


def upsert_skill(session: Session, skill_id: str, name: str, source_span: str) -> None:
    obj = session.get(Skill, skill_id)
    if obj is None:
        obj = Skill(skill_id=skill_id, name=name, source_span=source_span)
        session.add(obj)
    else:
        obj.name = name
        obj.source_span = source_span


def upsert_series(session: Session, series_id: str, skill_id: str, label: str, units: str, meta_json: str) -> None:
    obj = session.get(Series, series_id)
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
    obj = session.get(Analysis, series_id)
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
