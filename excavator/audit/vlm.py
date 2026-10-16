"""Level 2 - VLM sensory audit (sequence-level).

For cases with no text evidence, sample scenes, build a time-ordered
multi-camera strip image per scene, and ask the user's VLM whether the
sequence exercises the case. Constrained JSON output; per-claim provenance
(strip path + scene token); verdict by majority vote with vote breakdown.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from ..adapters.base import Scene
from ..llm import LlmClient
from ..reference import Case

MAX_STRIP_PX = 1280


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
        results: dict[str, dict] = {}
        cache = self.out_dir / "vlm_cache"
        cache.mkdir(parents=True, exist_ok=True)
        for case in cases:
            verdicts, evid = [], []
            for sc in scenes:
                key = hashlib.sha1(f"{case.case_id}|{sc.token}".encode()).hexdigest()[:16]
                cpath = cache / f"{key}.json"
                strip_path = cache / f"{key}.jpg"
                strip = self.build_strip(sc, strip_path)
                if strip is None:
                    continue
                if cpath.exists():
                    out = json.loads(cpath.read_text())
                else:
                    out = self._ask(case, strip)
                    cpath.write_text(json.dumps(out))
                verdicts.append(str(out.get("verdict", "unclear")))
                if out.get("verdict") == "present":
                    evid.append({"scene": sc.token, "strip": strip.name,
                                 "confidence": out.get("confidence"),
                                 "reason": out.get("reason")})
            results[case.case_id] = {
                "level": self.level,
                "verdict": _majority(verdicts),
                "votes": _tally(verdicts),
                "scenes_checked": len(verdicts),
                "evidence": evid,
            }
        return results

    def _ask(self, case: Case, strip_path: Path) -> dict:
        kw = ", ".join(case.keywords[:8]) or case.name
        system = ("You are auditing autonomous-driving scenario footage against a "
                  "safety-case spec. Judge only what is visually observable.")
        msg_user = (
            f"Case: {case.name}\nKeywords: {kw}\n"
            f"Case kind: {case.kind}\n\n"
            "The image is a contact sheet of one driving scene: rows are time "
            "steps, columns are the six surround cameras. Does this sequence "
            "visibly exhibit the case (actor class, misbehavior, state, factor, "
            "or situation)? Be conservative; answer 'unclear' if the footage "
            "cannot discriminate."
        )
        return self._vision_chat(system, msg_user, strip_path)

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
            return extract_json(text)
        except Exception:
            return {"verdict": "unclear", "confidence": 0.0,
                    "reason": f"unparseable: {text[:120]}"}


def _tally(verdicts: list[str]) -> dict:
    out: dict[str, int] = {}
    for v in verdicts:
        out[v] = out.get(v, 0) + 1
    return out


def _majority(verdicts: list[str]) -> str:
    if not verdicts:
        return "not_run"
    t = _tally(verdicts)
    if t.get("present", 0) > 0 and t["present"] >= max(t.values()):
        return "present"
    if t.get("absent", 0) == len(verdicts):
        return "absent"
    return "unclear"
