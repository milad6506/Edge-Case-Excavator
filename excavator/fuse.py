"""Fusion: combine per-level verdicts into final case verdicts and mine
corner-case candidates via leaf co-occurrence.

Final verdicts (v1 semantics, deliberately honest about evidence strength):
  COVERED           - keyword evidence, LLM close-read confirmed
  COVERED_WEAK      - keyword evidence, close-read says 'unclear'
  FALSE_POSITIVE    - keyword evidence rejected by close-read
  DETECTOR_PRESENT  - detector sweep found instances
  VLM_PRESENT       - VLM judged the sequence present (>=1 scene)
  TEXT_ABSENT       - no text evidence; queued for L2/L3 (absence not yet verified)
  MISSING_CANDIDATE - detectors (when run) and VLM (when run) and text all negative
  UNVERIFIED        - nothing ran for this case
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from .reference import Case

_FINAL = {
    ("text", "present"): "COVERED",
    ("text", "unclear"): "COVERED_WEAK",
    ("text", "false_positive"): "FALSE_POSITIVE",
    ("text", "absent"): None,
    ("vlm", "present"): "VLM_PRESENT",
    ("vlm", "unclear"): None,
    ("vlm", "absent"): None,
    ("detector", "present"): "DETECTOR_PRESENT",
    ("detector", "absent"): None,
}


def fuse_case(cases: dict[str, Case], results: dict[str, dict[str, dict]],
              executed_levels: set[str]) -> dict[str, dict]:
    """results: {level: {case_id: level_result}} -> {case_id: fused}"""
    fused: dict[str, dict] = {}
    for cid, case in cases.items():
        per_level = {lvl: (results.get(lvl, {}) or {}).get(cid) for lvl in executed_levels}
        present_levels, final = [], None
        details = {}
        for lvl, r in per_level.items():
            if r is None:
                continue
            details[lvl] = r
            v = r.get("verdict")
            if v in ("present", "unclear", "false_positive"):
                f = _FINAL.get((lvl, v))
                if f and (final is None or final == "COVERED_WEAK"):
                    final = f
                if v == "present":
                    present_levels.append(lvl)
        if final is None:
            detectors_ran = "detector" in executed_levels
            text_absent = details.get("text", {}).get("verdict") == "absent"
            vlm_negative = "vlm" not in executed_levels or \
                details.get("vlm", {}).get("verdict") in ("absent", "unclear")
            detector_negative = not detectors_ran or \
                details.get("detector", {}).get("verdict") == "absent"
            if text_absent:
                # MISSING only when the absence authorities (L3, L2) had their say
                final = "MISSING_CANDIDATE" if (detectors_ran and detector_negative
                                                and vlm_negative) else "TEXT_ABSENT"
            else:
                final = "UNVERIFIED"
        fused[cid] = {
            "case_id": cid, "kind": case.kind, "name": case.name,
            "verdict": final, "levels": details,
            "present_levels": sorted(present_levels),
        }
        if case.kind == "expectation":
            fused[cid]["source"] = case.meta.get("source_framework")
            fused[cid]["sequence"] = case.meta.get("sequence")
    return fused


def mine_corners(scene_hits: dict[str, set[str]], min_presence: int = 2,
                 max_pairs: int = 200) -> list[dict]:
    """Corner-case candidates from co-occurrence structure over leaf cases.

    Unrealized confluence: two leaves individually present across the corpus
    but never co-occurring in the same scene -> candidate corner case.
    Rare confluence (co-occurs once) -> realized but rare corner.
    """
    per_case_scenes = {cid: set(toks) for cid, toks in scene_hits.items()
                       if len(toks) >= min_presence}
    out = []
    for a, b in combinations(sorted(per_case_scenes), 2):
        sa, sb = per_case_scenes[a], per_case_scenes[b]
        if not sa or not sb:
            continue
        both = sa & sb
        item = {"pair": [a, b],
                "scenes_a": len(sa), "scenes_b": len(sb),
                "co_occurrence": len(both),
                "class": "unrealized_confluence" if not both else "rare_confluence"}
        if not both or len(both) == 1:
            out.append(item)
    out.sort(key=lambda x: (x["co_occurrence"], x["scenes_a"] + x["scenes_b"]))
    return out[:max_pairs]


def summarize(fused: dict[str, dict], corners: list[dict]) -> dict:
    by_verdict: dict[str, int] = defaultdict(int)
    by_kind: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    for f in fused.values():
        by_verdict[f["verdict"]] += 1
        by_kind[f["kind"]][f["verdict"]] += 1
    return {
        "total_cases": len(fused),
        "by_verdict": dict(by_verdict),
        "by_kind": {k: dict(v) for k, v in by_kind.items()},
        "corner_candidates": len(corners),
    }
