"""Level 1 - textual audit.

1a deterministic keyword sweep over the scene corpus (descriptions, QA pairs,
   annotation objects, scene descriptions)
1c optional LLM close-reading of keyword hits to kill false positives.
"""
from __future__ import annotations

import re
from collections import defaultdict

from ..adapters.base import Scene
from ..llm import LlmClient
from ..reference import Case


class TextAuditor:
    level = "text"

    def __init__(self, cases: list[Case], llm: LlmClient | None = None):
        self.cases = cases
        self.llm = llm

    def run(self, scenes: list[Scene], *, close_read: bool = True) -> dict[str, dict]:
        hits: dict[str, list[str]] = defaultdict(list)
        counts: dict[str, int] = defaultdict(int)
        snippets: dict[str, list[tuple[str, str]]] = defaultdict(list)
        rx = {c.case_id: c.primary_pattern() for c in self.cases}
        for sc in scenes:
            for kind, text in sc.corpus():
                for cid, pattern in rx.items():
                    m = pattern.search(text)
                    if m:
                        hits[cid].append(sc.token)
                        counts[cid] += 1
                        if len(snippets[cid]) < 3:
                            snippets[cid].append((sc.token, text[:180]))
        results: dict[str, dict] = {}
        for c in self.cases:
            n_scenes = len(set(hits.get(c.case_id, [])))
            if n_scenes == 0:
                results[c.case_id] = {"level": self.level, "verdict": "absent",
                                      "hit_count": 0, "scene_tokens": [],
                                      "snippets": []}
                continue
            verdict = "present"
            if close_read and self.llm is not None:
                verdict = self._close_read(c, snippets.get(c.case_id, []))
            results[c.case_id] = {"level": self.level, "verdict": verdict,
                                  "hit_count": counts[c.case_id],
                                  "scene_tokens": sorted(set(hits[c.case_id])),
                                  "snippets": [s for _, s in snippets[c.case_id]]}
        return results

    def _close_read(self, case: Case, snippets: list[tuple[str, str]], max_spans: int = 5) -> str:
        """1c: ask the judge model whether the matched text really evidences the case."""
        spans = "\n".join(f"- {s}" for _, s in snippets[:max_spans])
        prompt = (
            f"Case under test: {case.case_id} ({case.name}).\n"
            f"Definition/keywords: {', '.join(case.keywords) or case.name}\n\n"
            f"Text snippets from a driving scenario database:\n{spans}\n\n"
            "Does this textual evidence genuinely describe the case being present "
            "(actors, states, conditions, or expected behavior), or are the matches "
            "incidental word overlaps?"
        )
        try:
            out = self.llm.json_chat(
                "You are auditing scenario-database text evidence against a case spec.",
                prompt + '\nReply as JSON: {"verdict": "present|unclear|false_positive", "reason": "one line"}',
            )
        except Exception:
            return "present"  # keep deterministic fallback on API failure
        v = str(out.get("verdict", "")).lower()
        if v in ("present", "unclear", "false_positive"):
            return {"present": "present", "unclear": "unclear",
                    "false_positive": "false_positive"}[v]
        return "present"
