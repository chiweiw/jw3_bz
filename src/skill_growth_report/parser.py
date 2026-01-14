import re
from typing import List, Dict, Any, Tuple


def find_skills(text: str) -> List[Tuple[str, str, int, int]]:
    res: List[Tuple[str, str, int, int]] = []
    matches = list(re.finditer(r"(^|\n)\s*([^\n\-]+?)\s*-\s*(\d{5})\s*(?=\n)", text))
    for i, m in enumerate(matches):
        name = m.group(2).strip()
        sid = m.group(3).strip()
        start = m.end()
        if i < len(matches) - 1:
            end = matches[i+1].start()
        else:
            end = len(text)
        res.append((name, sid, start, end))
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

RESOURCES = ["精神值", "耐力值", "气血值", "内力", "精神", "耐力", "气血"]
RESOURCE_MAP = {
    "精神值": "精神",
    "精神": "精神",
    "耐力值": "耐力",
    "耐力": "耐力",
    "气血值": "气血",
    "气血": "气血",
    "内力": "内力",
}
ACTIONS = ["消耗", "造成", "回复", "恢复"]

def _detect_action(pre: str) -> str:
    if "消耗" in pre:
        return "消耗"
    if "回复" in pre or "恢复" in pre:
        return "回复"
    return "造成"

def _match_resource(label: str) -> Tuple[str, str]:
    for k in RESOURCES:
        if label.startswith(k) or k in label:
            return RESOURCE_MAP.get(k, k), k
    if "伤害" in label:
        return label, "伤害"
    if "打击" in label:
        if "精神" in label:
            return "精神", "精神"
        if "耐力" in label:
            return "耐力", "耐力"
    return "", ""


def extract_description(block: str) -> str:
    lines = block.split('\n')
    desc_lines = []
    for line in lines:
        l = line.strip()
        if not l:
            continue
        desc_lines.append(l)
    sanitized: List[str] = []
    for l in desc_lines:
        x = re.sub(r"<[^>]*>", "<>", l)
        x = re.sub(r"\s{2,}", " ", x).strip()
        sanitized.append(x)
    return "\n".join(sanitized)


def extract_sequences(block: str) -> List[Dict[str, Any]]:
    res: List[Dict[str, Any]] = []
    for m in re.finditer(r"<([^>]+)>\s*点([\u4e00-\u9fa5a-zA-Z0-9_]+?)(?=(使|对|回复|恢复|造成|并|，|。|、|;|；|:|：|（|）|\(|\)|\s))", block):
        seq = _parse_numbers(m.group(1))
        label = _normalize_label(m.group(2))
        pre = block[max(0, m.start() - 16):m.start()]
        action = _detect_action(pre)
        norm_res, _ = _match_resource(label)
        if seq:
            res.append({"label": label, "units": "点", "values": seq, "action": action, "resource": norm_res})
    for m in re.finditer(r"<([^>]+)>\s*([\u4e00-\u9fa5a-zA-Z0-9_]+伤害)", block):
        seq = _parse_numbers(m.group(1))
        label = _normalize_label(m.group(2))
        action = "造成"
        norm_res = label
        if seq:
            res.append({"label": label, "units": "点", "values": seq, "action": action, "resource": norm_res})
    return res


def extract_special_effects(block: str) -> List[str]:
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    res: List[str] = []
    for l in lines:
        if "<" in l and ">" in l and ("点" in l or "伤害" in l):
            continue
        if ("招式到达三重" in l or "招式达到三重" in l) and not ("若" in l or "当" in l):
            continue
        triggers = [
            "被动效果",
            "若命中目标",
            "若招式命中目标",
            "若目标",
            "当命中",
            "招式命中目标",
            "命中目标，则",
            "命中目标则",
            "当门派为",
            "当门派兵器为",
            "当使用者为",
            "当心法为",
            "若使用者门派兵器为",
            "若使用者门派为",
            "若使用者心法为",
            "若心法为",
            "目标气血值低于",
            "目标气血值高于",
            "若释放时",
            "若招式会心",
            "若招式击破",
            "若选中敌对非侠士目标",
            "目标精神高于",
            "目标精神低于",
            "目标耐力高于",
            "目标耐力低于",
        ]
        for t in triggers:
            if t in l:
                res.append(l)
                break
    return res
