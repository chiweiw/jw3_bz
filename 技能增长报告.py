import re
import os
import argparse
from typing import List, Dict, Any, Tuple

def read_text(fp: str) -> str:
    with open(fp, "r", encoding="utf-8") as f:
        return f.read()

def find_skills(text: str) -> List[Tuple[str, str, int, int]]:
    skills = []
    for m in re.finditer(r"(^|\n)\s*([^\n\-]+?)\s*-\s*(\d{5})\s*(?=\n)", text):
        start = m.end()
        skills.append((m.group(2).strip(), m.group(3).strip(), start, -1))
    for i in range(len(skills)):
        s = skills[i]
        end = len(text) if i == len(skills) - 1 else skills[i + 1][2] - len("\n")
        skills[i] = (s[0], s[1], s[2], end)
    return skills

def normalize_label(label: str) -> str:
    label = label.strip()
    label = label.replace("点", "")
    label = label.replace("/", "_")
    label = label.replace(" ", "")
    return label

def parse_numbers(seq: str) -> List[float]:
    parts = [p.strip() for p in seq.split("/")]
    vals = []
    for p in parts:
        p = p.replace(",", "")
        try:
            vals.append(float(p))
        except Exception:
            pass
    return vals

def extract_sequences(block: str) -> List[Dict[str, Any]]:
    res = []
    for m in re.finditer(r"<([^>]+)>\s*点([\u4e00-\u9fa5a-zA-Z0-9_]+)", block):
        seq = parse_numbers(m.group(1))
        label = normalize_label(m.group(2))
        pre = block[max(0, m.start() - 12):m.start()]
        if "消耗" in pre:
            label = "消耗-" + label
        if "减少" in pre:
            label = "减少-" + label
        if seq:
            res.append({"label": label, "values": seq})
    for m in re.finditer(r"<([^>]+)>\s*([\u4e00-\u9fa5a-zA-Z0-9_]+伤害)", block):
        seq = parse_numbers(m.group(1))
        label = normalize_label(m.group(2))
        pre = block[max(0, m.start() - 12):m.start()]
        if "消耗" in pre:
            label = "消耗-" + label
        if "减少" in pre:
            label = "减少-" + label
        if seq:
            res.append({"label": label, "values": seq})
    return res

def analyze(values: List[float]) -> Dict[str, Any]:
    diffs = []
    for i in range(len(values) - 1):
        diffs.append(values[i + 1] - values[i])
    is_linear = False
    if diffs:
        s = set(round(d, 8) for d in diffs)
        is_linear = len(s) == 1
    monotonic = "mixed"
    if diffs and all(d >= 0 for d in diffs):
        monotonic = "increasing"
    elif diffs and all(d <= 0 for d in diffs):
        monotonic = "decreasing"
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "diffs": diffs,
        "is_linear": is_linear,
        "monotonic": monotonic,
    }

def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)

def plot_series(out_dir: str, skill_key: str, label: str, values: List[float]) -> None:
    try:
        import matplotlib.pyplot as plt
        ensure_dir(os.path.join(out_dir, skill_key))
        plt.figure(figsize=(8, 4))
        xs = list(range(1, len(values) + 1))
        plt.plot(xs, values, marker="o")
        plt.xlabel("Level")
        plt.ylabel(label)
        plt.title(f"{skill_key} - {label}")
        fp = os.path.join(out_dir, skill_key, f"{label}.png")
        plt.tight_layout()
        plt.savefig(fp)
        plt.close()
    except Exception:
        pass

def unique_label(existing: Dict[str, Any], label: str) -> str:
    if label not in existing:
        return label
    i = 2
    while True:
        cand = f"{label}#{i}"
        if cand not in existing:
            return cand
        i += 1

def generate_report(input_fp: str, out_dir: str) -> None:
    text = read_text(input_fp)
    skills = find_skills(text)
    for name, sid, start, end in skills:
        block = text[start:end]
        seqs = extract_sequences(block)
        skill_key = f"{sid}-{name}"
        store: Dict[str, Any] = {}
        for item in seqs:
            label = unique_label(store, item["label"])
            store[label] = item["values"]
        print(f"技能: {name} ({sid})")
        print(f"序列数: {len(store)}")
        for label, values in store.items():
            a = analyze(values)
            print(f"- {label}")
            print(f"  值: {values}")
            print(f"  差值: {a['diffs']}")
            print(f"  线性: {'是' if a['is_linear'] else '否'}  趋势: {a['monotonic']}")
            plot_series(out_dir, skill_key, label, values)
        print("")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=os.path.join("excel转实体类", "1.txt"))
    parser.add_argument("--output-dir", default=os.path.join("excel转实体类", "报告输出"))
    args = parser.parse_args()
    generate_report(args.input, args.output_dir)

if __name__ == "__main__":
    main()

