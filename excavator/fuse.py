"""Fusion: combine per-level verdicts into final case verdicts and mine
corner-case candidates via leaf co-occurrence.

Final verdicts (v1 semantics, deliberately honest about evidence strength):
  COVERED           - text evidence confirmed (or at least present at text level)
  DETECTOR_PRESENT  - detector found instances (overrides text rejection)
  VLM_PRESENT       - VLM judged the sequence present (overrides text rejection)
  COVERED_WEAK      - keyword evidence, close-read says 'unclear'
  FALSE_POSITIVE    - text evidence rejected, no other level confirms presence
  MISSING_CANDIDATE - text negative AND every executed level that produced a
                      verdict for the case reports 'absent' (the VLM level must
                      have executed; actor-kind cases additionally require the
                      detector level to be negative — detectors are the
                      absence authority for actor classes)
  TEXT_ABSENT       - no text evidence; queued for L2/L3 (absence unverified)
  UNVERIFIED        - nothing ran for this case
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from .reference import Case

_PRESENCE_PRIORITY = (("text", "COVERED"), ("detector", "DETECTOR_PRESENT"),
                      ("vlm", "VLM_PRESENT"))


def fuse_case(cases: dict[str, Case], results: dict[str, dict[str, dict]],
              executed_levels: set[str]) -> dict[str, dict]:
    """results: {level: {case_id: level_result}} -> {case_id: fused}"""
    fused: dict[str, dict] = {}
    for cid, case in cases.items():
        per_level = {lvl: (results.get(lvl, {}) or {}).get(cid) for lvl in executed_levels}
        details = {lvl: r for lvl, r in per_level.items() if r is not None}
        present_levels = [lvl for lvl, r in details.items() if r.get("verdict") == "present"]
        final = None
        for lvl, verdict_name in _PRESENCE_PRIORITY:
            if lvl in present_levels:
                final = verdict_name
                break
        text_verdict = details.get("text", {}).get("verdict")
        if final is None and text_verdict == "unclear":
            final = "COVERED_WEAK"
        if final is None:
            if text_verdict in ("absent", "false_positive"):
                others_negative = all(r.get("verdict") == "absent"
                                      for lvl, r in details.items() if lvl != "text")
                sensory_ran = "vlm" in executed_levels and \
                    (case.kind != "actor" or "detector" in executed_levels)
                if others_negative and sensory_ran:
                    final = "MISSING_CANDIDATE"
                elif text_verdict == "false_positive":
                    final = "FALSE_POSITIVE"
                else:
                    final = "TEXT_ABSENT"
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
