"""Engine tests — offline only (no API, no dataset required)."""
import json
from pathlib import Path

import pytest

from excavator.adapters import get_adapter
from excavator.audit.text import TextAuditor
from excavator.fuse import fuse_case, mine_corners, summarize
from excavator.reference import Reference

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def reference():
    return Reference(ROOT / "reference")


def test_reference_registry_counts(reference):
    stats = reference.stats()
    assert stats["cases"]["actor"] == 42
    assert stats["cases"]["misbehavior"] == 49
    assert stats["cases"]["expectation"] == 221
    assert reference.version == "6.0"


def test_filter_scopes(reference):
    leaves = reference.filter("leaves", ".*")
    exps = reference.filter("expectations", ".*")
    assert leaves and exps
    assert all(c.kind != "expectation" for c in leaves)
    assert {c.kind for c in exps} == {"expectation"}
    fam = reference.filter("all", r"^MISBEHAVIOR:.*")
    assert fam and all(c.case_id.startswith("MISBEHAVIOR:") for c in fam)


def test_phrase_matching(reference):
    case = next(c for c in reference.cases if c.case_id.endswith("Passenger Light Vehicles"))
    rx = case.primary_pattern()
    assert rx.search("A silver sedan and two SUVs wait at the light.")
    assert rx.search("passenger light vehicles dominate the scene")
    assert not rx.search("a passenger train passed the light vehicle museum")


def test_text_auditor_verdicts(reference):
    from excavator.adapters.base import Frame, Scene, TextRecord
    scenes = [Scene(token="s1", name="t", frames=[
        Frame(token="f1", scene_token="s1", index=0,
              texts=[TextRecord("qa", "A pedestrian with a stroller crosses.")])]),
        Scene(token="s2", name="t", frames=[
            Frame(token="f2", scene_token="s2", index=0,
                  texts=[TextRecord("qa", "The road is empty.")])])]
    cases = reference.filter("leaves", r"^ACTOR:.*Strollers")
    assert cases, "stroller actor case missing"
    res = TextAuditor(cases).run(scenes, close_read=False)
    assert res[cases[0].case_id]["verdict"] == "present"
    assert res[cases[0].case_id]["scene_tokens"] == ["s1"]


def test_fusion_text_only_absent_is_not_missing(reference):
    cases = {c.case_id: c for c in reference.filter("leaves", r"^MISBEHAVIOR:RUNNING_RED")}
    cid = next(iter(cases))
    results = {"text": {cid: {"level": "text", "verdict": "absent"}}}
    fused = fuse_case(cases, results, executed_levels={"text"})
    assert fused[cid]["verdict"] == "TEXT_ABSENT"

    results2 = {"text": {cid: {"level": "text", "verdict": "absent"}},
                "detector": {cid: {"level": "detector", "verdict": "absent"}}}
    fused2 = fuse_case(cases, results2, executed_levels={"text", "detector"})
    assert fused2[cid]["verdict"] == "MISSING_CANDIDATE"

    results3 = {"text": {cid: {"level": "text", "verdict": "present"}}}
    fused3 = fuse_case(cases, results3, executed_levels={"text"})
    assert fused3[cid]["verdict"] == "COVERED"


def test_corner_mining():
    hits = {"A": {"s1", "s2", "s3"}, "B": {"s1"}, "C": {"s4"}}
    corners = mine_corners(hits)
    pair = {(c["pair"][0], c["pair"][1]): c for c in corners}
    assert pair[("A", "B")]["class"] == "rare_confluence"
    assert pair[("A", "C")]["class"] == "unrealized_confluence"


def test_summarize_shape():
    fused = {"x": {"kind": "actor", "verdict": "COVERED", "levels": {}}}
    s = summarize(fused, [])
    assert s["total_cases"] == 1 and s["by_verdict"]["COVERED"] == 1


def test_drivelm_adapter_offline(reference):
    root = Path("~/Documents/DriveLM").expanduser()
    if not (root / "v1_1_train_nus.json").exists():
        pytest.skip("local DriveLM data not present")
    ad = get_adapter("drivelm", root, None)
    scenes = ad.load(3)
    assert len(scenes) == 3
    sc = scenes[0]
    assert sc.frames and sc.frames[0].texts
    kinds = {k for k, _ in sc.corpus()}
    assert kinds <= {"description", "qa", "annotation", "scene_description"}
