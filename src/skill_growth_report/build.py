import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from .parser import find_skills, extract_sequences, extract_description, extract_special_effects
from .analyzer import analyze, diffs
from .dbkit.base import get_session
from .dbkit.crud import upsert_skill, upsert_series, replace_values, upsert_analysis
from .export import export_all, ensure_dir

def unique_label(existing: Dict[str, Any], label: str) -> str:
    if label not in existing:
        return label
    i = 2
    while True:
        cand = f"{label}#{i}"
        if cand not in existing:
            return cand
        i += 1


def run(input_fp: Path, site_dir: Path, db_path: Path, jump_threshold: float, cname: Optional[str] = None) -> None:
    text = input_fp.read_text(encoding="utf-8")
    skills_blocks = find_skills(text)
    ensure_dir(site_dir)
    session = get_session(db_path)
    skills_out: List[Dict[str, Any]] = []
    series_out: List[Dict[str, Any]] = []
    values_out: Dict[str, List[Dict[str, Any]]] = {}
    analyses_out: Dict[str, Dict[str, Any]] = {}
    for name, sid, start, end in skills_blocks:
        block = text[start:end]
        seqs = extract_sequences(block)
        desc = extract_description(block)
        effects = extract_special_effects(block)
        groups: Dict[str, Dict[str, List[Dict[str, Any]]]] = {"consume": {}, "deal": {}, "recover": {}}
        def push(bucket: Dict[str, List[Dict[str, Any]]], key: str, item: Dict[str, Any]) -> None:
            bucket.setdefault(key, []).append({"label": item["label"], "values": item["values"]})
        for it in seqs:
            act = it.get("action")
            res_name = it.get("resource") or ""
            lab = it.get("label")
            if act == "消耗" and res_name in ("精神", "耐力", "气血", "内力"):
                push(groups["consume"], res_name, it)
            elif act in ("回复", "恢复") and res_name in ("精神", "耐力", "气血", "内力"):
                push(groups["recover"], res_name, it)
            else:
                if lab.endswith("伤害"):
                    push(groups["deal"], lab, it)
                elif act == "造成" and res_name in ("精神", "耐力"):
                    push(groups["deal"], res_name + "打击", it)
        skill_meta: Dict[str, Any] = {}
        if "招式到达三重" in block or "招式达到三重" in block:
            skill_meta["has_threefold"] = True
            if "不再消耗精神" in block:
                skill_meta["threefold_no_spirit_cost"] = True
            if "偷取目标" in block and "精神" in block:
                skill_meta["steal_spirit"] = True
        upsert_skill(session, sid, name, json.dumps({"start": start, "end": end, "meta": skill_meta, "description": desc, "desc_template": desc, "special_effects": effects, "full_text": block, "groups": groups}))
        skills_out.append({"skill_id": sid, "name": name, "meta": skill_meta, "description": desc, "desc_template": desc, "special_effects": effects, "full_text": block, "groups": groups})
        store: Dict[str, Any] = {}
        for item in seqs:
            label = unique_label(store, item["label"])
            store[label] = item["values"]
            series_id = f"{sid}:{label}"
            upsert_series(session, series_id, sid, label, item["units"], json.dumps({}))
            ds = diffs(item["values"]) if len(item["values"]) > 1 else []
            rows: List[Dict[str, Any]] = []
            for idx, v in enumerate(item["values"], start=1):
                d = None
                if idx > 1:
                    d = v - item["values"][idx - 2]
                rows.append({"level_index": idx, "value": v, "diff_to_prev": d, "is_jump": False})
            a = analyze(item["values"], jump_threshold)
            for jp in a["jump_points"]:
                if 1 <= jp <= len(rows):
                    rows[jp - 1]["is_jump"] = True
            replace_values(session, series_id, rows)
            upsert_analysis(session, series_id, a, json.dumps(a["jump_points"]))
            series_out.append({"series_id": series_id, "skill_id": sid, "label": label, "units": item["units"], "meta": {}})
            values_out[series_id] = rows
            analyses_out[series_id] = a
    session.commit()
    session.close()
    export_all(site_dir, skills_out, series_out, values_out, analyses_out)


def copy_frontend(site_dir: Path, cname: Optional[str]) -> None:
    # We only handle CNAME and .nojekyll generation here.
    # The HTML/JS/CSS files should already exist in the site_dir (docs folder)
    # and are maintained there directly.
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")
    if cname:
        (site_dir / "CNAME").write_text(cname.strip(), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="1.txt")
    p.add_argument("--site-dir", default="docs")
    p.add_argument("--db-path", default="skill_report.db")
    p.add_argument("--jump-threshold", type=float, default=2.0)
    p.add_argument("--cname", default=None)
    args = p.parse_args()
    run(Path(args.input), Path(args.site_dir), Path(args.db_path), args.jump_threshold, args.cname)


if __name__ == "__main__":
    main()

