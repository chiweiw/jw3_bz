import re
from typing import List, Dict, Any, Tuple


def find_skills(text: str) -> List[Tuple[str, str, int, int]]:
    res: List[Tuple[str, str, int, int]] = []
    for m in re.finditer(r"(^|\n)\s*([^\n\-]+?)\s*-\s*(\d{5})\s*(?=\n)", text):
        start = m.end()
        res.append((m.group(2).strip(), m.group(3).strip(), start, -1))
    for i in range(len(res)):
        s = res[i]
        end = len(text) if i == len(res) - 1 else res[i + 1][2] - len("\n")
        res[i] = (s[0], s[1], s[2], end)
    return res


def _normalize_label(label: str) -> str:
    x = label.strip()
    x = x.replace("点", "")
    x = x.replace("/", "_")
    x = x.replace(" ", "")
    return x


def _parse_numbers(seq: str) -> List[float]:
    parts = [p.strip() for p in seq.split("/")]
    vals: List[float] = []
    for p in parts:
        p = p.replace(",", "")
        try:
            vals.append(float(p))
        except Exception:
            pass
    return vals


def extract_sequences(block: str) -> List[Dict[str, Any]]:
    res: List[Dict[str, Any]] = []
    for m in re.finditer(r"<([^>]+)>\s*点([\u4e00-\u9fa5a-zA-Z0-9_]+)", block):
        seq = _parse_numbers(m.group(1))
        label = _normalize_label(m.group(2))
        pre = block[max(0, m.start() - 16):m.start()]
        if "消耗" in pre:
            label = "消耗-" + label
        if "减少" in pre:
            label = "减少-" + label
        if seq:
            res.append({"label": label, "units": "点", "values": seq})
    for m in re.finditer(r"<([^>]+)>\s*([\u4e00-\u9fa5a-zA-Z0-9_]+伤害)", block):
        seq = _parse_numbers(m.group(1))
        label = _normalize_label(m.group(2))
        pre = block[max(0, m.start() - 16):m.start()]
        if "消耗" in pre:
            label = "消耗-" + label
        if "减少" in pre:
            label = "减少-" + label
        if seq:
            res.append({"label": label, "units": "点", "values": seq})
    return res

