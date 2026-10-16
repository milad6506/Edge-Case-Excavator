"""Level 1 - textual audit (sequence-level).

Assessment unit: the scenario sequence (a Scene). Text evidence from all
frames, cameras and QA records of a sequence is pooled; a case is text-covered
if ANY sequence in the corpus evidences it. Frame granularity never produces
verdicts on its own.

1a deterministic keyword sweep over the pooled corpus (descriptions, QA pairs,
   annotation objects, scene descriptions)
1c optional LLM close-reading of keyword hits (parallel) to kill false
   positives.
"""
from __future__ import annotations

import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..adapters.base import Scene
from ..llm import LlmClient
from ..reference import Case

CLOSE_READ_WORKERS = 8
CLOSE_READ_MAX_TOKENS = 4000  # reasoning models need headroom

# negation guard: "Are there X? No." / "There are no X" / "no X ahead"
_NEG_BEFORE = re.compile(r"\b(no|not|none|never|without|zero|n't)\b[^.]{0,15}$", re.I)


def _is_negated(text: str, m_start: int) -> bool:
    tl = text.lower().rstrip()
    if tl.endswith(" no.") or tl.endswith(" no") or tl.endswith("none."):
        return True  # negative QA answer (bare 'No.')
    before = text[max(0, m_start - 30):m_start]
    return bool(_NEG_BEFORE.search(before))


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
                if not text:
                    continue
                for cid, pattern in rx.items():
                    m = pattern.search(text)
                    if m and not _is_negated(text, m.start()):
                        hits[cid].append(sc.token)
                        counts[cid] += 1
                        if len(snippets[cid]) < 5:
                            snippets[cid].append((sc.token, text[:180]))

        results: dict[str, dict] = {}
        pending: list[tuple[Case, list[tuple[str, str]]]] = []
        for c in self.cases:
            n_scenes = len(set(hits.get(c.case_id, [])))
            if n_scenes == 0:
                results[c.case_id] = {"level": self.level, "verdict": "absent",
                                      "hit_count": 0, "scene_tokens": [],
                                      "snippets": []}
                continue
            if close_read and self.llm is not None:
                pending.append((c, snippets[c.case_id]))
                continue
            results[c.case_id] = self._present(c, counts, hits, snippets, "present")

        if pending:
            with ThreadPoolExecutor(max_workers=CLOSE_READ_WORKERS) as pool:
                futs = {pool.submit(self._close_read, c, snips): c
                        for c, snips in pending}
                for fut in as_completed(futs):
                    c = futs[fut]
                    verdict, reason = fut.result()
                    results[c.case_id] = self._present(c, counts, hits, snippets,
                                                       verdict, reason)
        return results

    @staticmethod
    def _present(case, counts, hits, snippets, verdict, reason=None) -> dict:
        out = {"level": "text", "verdict": verdict,
               "hit_count": counts[case.case_id],
               "scene_tokens": sorted(set(hits[case.case_id])),
               "snippets": [s for _, s in snippets[case.case_id]]}
        if reason:
            out["close_read_reason"] = reason
        return out

    def _close_read(self, case: Case, snippets: list[tuple[str, str]], max_spans: int = 5) -> tuple[str, str]:
        """1c: ask the judge model whether the matched text really evidences the case."""
        spans = "\n".join(f"- {s}" for _, s in snippets[:max_spans])
        prompt = (
            f"Case under test: {case.case_id} ({case.name}).\n"
            f"Definition/keywords: {', '.join(case.keywords) or case.name}\n\n"
            f"Text snippets from a driving scenario database:\n{spans}\n\n"
            "Rules of judgment:\n"
            "- For broad actor classes, a generic category mention counts as presence "
            "(e.g. 'one truck' evidences Heavy Commercial Trucks; 'a car' evidences "
            "Passenger Light Vehicles).\n"
            "- Negative QA answers ('Are there X? No.') are ABSENCE evidence, not presence.\n"
            "- Answer false_positive only when EVERY snippet is an incidental word "
            "overlap with no bearing on the case."
        )
        try:
            out = self.llm.json_chat(
                "You are auditing scenario-database text evidence against a case spec.",
                prompt + '\nReply as JSON: {"verdict": "present|unclear|false_positive", "reason": "one line"}',
                max_tokens=CLOSE_READ_MAX_TOKENS,
            )
        except Exception:
            return "present", "close-read failed; deterministic fallback"
        v = str(out.get("verdict", "")).lower()
        verdict = {"present": "present", "unclear": "unclear",
                   "false_positive": "false_positive"}.get(v, "present")
        return verdict, str(out.get("reason", ""))[:200]
