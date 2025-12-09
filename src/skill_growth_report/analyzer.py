from typing import List, Dict, Any


def diffs(values: List[float]) -> List[float]:
    ds: List[float] = []
    for i in range(len(values) - 1):
        ds.append(values[i + 1] - values[i])
    return ds


def is_linear(diffs_list: List[float]) -> bool:
    if not diffs_list:
        return False
    s = set(round(d, 8) for d in diffs_list)
    return len(s) == 1


def trend(diffs_list: List[float]) -> str:
    if not diffs_list:
        return "mixed"
    if all(d >= 0 for d in diffs_list):
        return "increasing"
    if all(d <= 0 for d in diffs_list):
        return "decreasing"
    return "mixed"


def jumps(diffs_list: List[float], threshold: float) -> List[int]:
    if not diffs_list:
        return []
    base = sorted(abs(d) for d in diffs_list)
    mid = base[len(base) // 2] if base else 0.0
    res: List[int] = []
    for i, d in enumerate(diffs_list):
        if d > 0 and mid > 0 and d >= mid * threshold:
            res.append(i + 2)
    return res


def analyze(values: List[float], threshold: float) -> Dict[str, Any]:
    ds = diffs(values)
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "diffs": ds,
        "is_linear": is_linear(ds),
        "trend": trend(ds),
        "jump_points": jumps(ds, threshold),
    }

