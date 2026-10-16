"""Level 2 - VLM sensory audit (sequence-level).

For cases without text evidence, sample scenes, build a time-ordered
multi-camera strip image per scene, and ask the user's VLM whether the
sequence exercises the case. Constrained JSON output; per-claim provenance
(strip path + scene token); verdict by majority vote with vote breakdown.
Pairs are judged in parallel (thread pool)."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

from ..adapters.base import Scene
from ..llm import LlmClient
from ..reference import Case

MAX_STRIP_PX = 1280
VLM_WORKERS = 8


class VlmAuditor:
    level = "vlm"

    def __init__(self, llm: LlmClient, out_dir: Path,
                 scenes_per_case: int = 6, strip_frames: int = 6,
                 camera_order: tuple[str, ...] = ("CAM_FRONT", "CAM_FRONT_LEFT",
                                                  "CAM_FRONT_RIGHT", "CAM_BACK_LEFT",
                                                  "CAM_BACK", "CAM_BACK_RIGHT")):
        self.llm = llm
        self.out_dir = Path(out_dir)
        self.scenes_per_case = scenes_per_case
        self.strip_frames = strip_frames
        self.cameras = camera_order

    # -- strip construction -------------------------------------------------
    def build_strip(self, scene: Scene, dest: Path) -> Path | None:
        """Time x camera contact sheet: keyframes down the rows, cameras across."""
        picks: list[list[Image.Image | None]] = []
        chosen = self._pick_frames(scene)
        for frame in chosen:
            row: list[Image.Image | None] = []
            for cam in self.cameras:
                p = frame.images.get(cam)
                if p and Path(p).exists():
                    img = Image.open(p).convert("RGB")
                    img.thumbnail((400, 225))
                    row.append(img)
                else:
                    row.append(None)
            picks.append(row)
        picks = [r for r in picks if any(c is not None for c in r)]
        if not picks:
            return None
        cols = max(len(r) for r in picks)
        cw, ch = 400, 225
        sheet = Image.new("RGB", (cols * cw, len(picks) * ch), (18, 18, 18))
        for r, row in enumerate(picks):
            for c, img in enumerate(row):
                if img is not None:
                    sheet.paste(img, (c * cw, r * ch))
        if sheet.width > MAX_STRIP_PX:
            sheet.thumbnail((MAX_STRIP_PX, MAX_STRIP_PX))
        dest.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(dest, "JPEG", quality=85)
        return dest

    def _pick_frames(self, scene: Scene):
        frames = [f for f in scene.frames if f.images]
        if not frames:
            return []
        n = min(self.strip_frames, len(frames))
        step = max(1, len(frames) // n)
        return frames[::step][:n]

    # -- audit --------------------------------------------------------------
    def run(self, cases: list[Case], scenes: list[Scene], *, limit_per_case: int | None = None) -> dict[str, dict]:
        scenes = scenes[: limit_per_case or self.scenes_per_case]
        cache = self.out_dir / "vlm_cache"
        cache.mkdir(parents=True, exist_ok=True)
        pairs = [(case, sc) for case in cases for sc in scenes]
        verdicts: dict[str, list[str]] = {c.case_id: [] for c in cases}
        evidence: dict[str, list[dict]] = {c.case_id: [] for c in cases}

        def work(pair):
            case, sc = pair
            key = hashlib.sha1(f"{case.case_id}|{sc.token}".encode()).hexdigest()[:16]
            cpath = cache / f"{key}.json"
            strip_path = cache / f"{key}.jpg"
            strip = self.build_strip(sc, strip_path)
            if strip is None:
                return case.case_id, None, None
            if cpath.exists():
                out = json.loads(cpath.read_text())
            else:
                out = self._ask(case, strip)
                cpath.write_text(json.dumps(out))
            return case.case_id, str(out.get("verdict", "unclear")), {
                "scene": sc.token, "strip": strip.name,
                "confidence": out.get("confidence"), "reason": out.get("reason")}

        with ThreadPoolExecutor(max_workers=VLM_WORKERS) as pool:
            futs = [pool.submit(work, p) for p in pairs]
            for fut in as_completed(futs):
                cid, verdict, ev = fut.result()
                if verdict is None:
                    continue
                verdicts[cid].append(verdict)
                if verdict == "present" and ev:
                    evidence[cid].append(ev)

        results: dict[str, dict] = {}
        for case in cases:
            v = verdicts[case.case_id]
            results[case.case_id] = {
                "level": self.level,
                "verdict": _majority(v),
                "votes": _tally(v),
                "scenes_checked": len(v),
                "evidence": evidence[case.case_id],
            }
        return results

    def _ask(self, case: Case, strip_path: Path) -> dict:
        kw = ", ".join(case.keywords[:8]) or case.name
        kind_guidance = {
            "actor": "the physical presence of this actor class in any frame",
            "misbehavior": "a road user visibly committing this specific misbehavior",
            "state": "this signaling/lighting state being visibly active",
            "factor": "this environmental or infrastructure condition being visible",
            "band": "this condition being visually identifiable",
            "buffer": "this clearance/situation being observable",
            "expectation": "the triggering situation of this behavioral expectation occurring",
        }.get(case.kind, "this case being visibly exhibited")
        user = (
            f"Case: {case.name}\nKind: {case.kind}\nKeywords: {kw}\n"
            f"Decide whether the sequence shows {kind_guidance}.\n\n"
            "The image is a contact sheet of ONE driving scene: rows are time "
            "steps (earliest top), columns are the six surround cameras.\n\n"
            "Be decisive: answer 'present' when the case is visible in at least "
            "one tile, 'absent' when you can see it is not, and 'unclear' only "
            "when the footage genuinely cannot discriminate (occlusion, "
            "resolution, ambiguity)."
        )
        return self._vision_chat(
            "You are auditing autonomous-driving scenario footage against a "
            "safety-case spec. Judge only what is visually observable.",
            user, strip_path)

    def _vision_chat(self, system: str, user: str, strip_path: Path) -> dict:
        from ..llm import extract_json
        messages = [
            {"role": "system", "content": system +
                "\nRespond with a single JSON object. No markdown."},
            {"role": "user", "content": [
                {"type": "text", "text": user},
                self.llm.image_part(strip_path),
            ]},
        ]
        text = self.llm.chat(messages, temperature=0.0)
        try:
            out = extract_json(text)
        except Exception:
            return {"verdict": "unclear", "confidence": 0.0,
                    "reason": f"unparseable: {text[:120]}"}
        # tolerate alternative key names some models prefer
        if "verdict" not in out:
            for alt in ("judgment", "answer", "decision", "result"):
                if alt in out:
                    out["verdict"] = out[alt]
                    break
        v = str(out.get("verdict", "unclear")).lower()
        if v not in ("present", "absent", "unclear"):
            out["verdict"] = "unclear"
        return out


def _tally(verdicts: list[str]) -> dict:
    out: dict[str, int] = {}
    for v in verdicts:
        out[v] = out.get(v, 0) + 1
    return out


def _majority(verdicts: list[str]) -> str:
    """Sequence-level verdict from per-scene judgments: a single sighting is
    presence (recall-first, votes + evidence recorded for audit); absence
    requires every scene judged absent."""
    if not verdicts:
        return "not_run"
    t = _tally(verdicts)
    if t.get("present", 0) >= 1:
        return "present"
    if t.get("absent", 0) == len(verdicts):
        return "absent"
    return "unclear"
