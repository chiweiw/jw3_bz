import json
from pathlib import Path
from typing import Dict, Any, List


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_json(fp: Path, data: Any) -> None:
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def export_all(site_dir: Path, skills: List[Dict[str, Any]], series: List[Dict[str, Any]], values: Dict[str, List[Dict[str, Any]]], analyses: Dict[str, Dict[str, Any]]) -> None:
    data_dir = site_dir / "data"
    ensure_dir(data_dir)
    skills_out = [{"skill_id": s["skill_id"], "name": s["name"], "meta": s.get("meta", {}), "description": s.get("description", ""), "desc_template": s.get("desc_template", ""), "special_effects": s.get("special_effects", []), "full_text": s.get("full_text", ""), "groups": s.get("groups", {})} for s in skills]
    write_json(data_dir / "skills.json", skills_out)
    write_json(
        data_dir / "series.json",
        [
            {
                "series_id": x["series_id"],
                "skill_id": x["skill_id"],
                "label": x["label"],
                "units": x["units"],
                "meta": x.get("meta", {}),
            }
            for x in series
        ],
    )
    write_json(
        data_dir / "values.json",
        {
            sid: [
                {
                    "level_index": v["level_index"],
                    "value": v["value"],
                    "diff_to_prev": v.get("diff_to_prev"),
                    "is_jump": v.get("is_jump", False),
                }
                for v in lst
            ]
            for sid, lst in values.items()
        },
    )
    write_json(
        data_dir / "analysis.json",
        {
            sid: {
                "is_linear": a.get("is_linear", False),
                "trend": a.get("trend", "mixed"),
                "min": a.get("min"),
                "max": a.get("max"),
                "count": a.get("count", 0),
                "jump_points": a.get("jump_points", []),
            }
            for sid, a in analyses.items()
        },
    )
