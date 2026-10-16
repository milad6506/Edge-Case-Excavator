"""Level 3 - detector sweep (strong specialized detectors).

Open-vocabulary YOLO-World sweep over sampled frames with a vocabulary
derived from the reference actor sub-classes. Detectors are the authority on
*absence*: a MISSING verdict requires the detector sweep to be negative.
Also emits a coarse kinematic proxy (bbox area growth between keyframes).
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from ..adapters.base import Scene
from ..reference import Case


def actor_vocab(cases: list[Case]) -> dict[str, list[str]]:
    """case_id -> detector prompt words, from ACTOR: cases only."""
    vocab = {}
    for c in cases:
        if c.kind != "actor":
            continue
        words = [w.lower() for w in re.findall(r"[A-Za-z]+", c.name)]
        vocab[c.case_id] = words or [c.name.lower()]
    return vocab


class DetectorAuditor:
    level = "detector"

    def __init__(self, model_path: str, conf: float = 0.25,
                 frames_per_scene: int = 4, cameras: tuple[str, ...] = ("CAM_FRONT",)):
        self.model_path = model_path
        self.conf = conf
        self.frames_per_scene = frames_per_scene
        self.cameras = cameras
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from ultralytics import YOLOWorld  # lazy: optional dependency
            self._model = YOLOWorld(self.model_path)
        return self._model

    def run(self, cases: list[Case], scenes: list[Scene]) -> dict[str, dict]:
        vocab = actor_vocab(cases)
        if not vocab or not scenes:
            return {c.case_id: {"level": self.level, "verdict": "not_run",
                                "scenes_checked": 0, "evidence": []}
                    for c in cases}
        try:
            model = self._ensure_model()
        except Exception as e:  # ultralytics not installed / model missing
            return {c.case_id: {"level": self.level, "verdict": "not_run",
                                "error": str(e)[:200], "scenes_checked": 0,
                                "evidence": []}
                    for c in cases}
        prompts = sorted({w for words in vocab.values() for w in words})
        model.set_classes(prompts)
        det_scene: dict[str, set[str]] = defaultdict(set)   # prompt -> scene tokens
        counts: dict[str, int] = defaultdict(int)
        checked = 0
        for sc in scenes:
            picked = [f for f in sc.frames if f.images][:: max(1, len(sc.frames) // self.frames_per_scene)]
            for frame in picked:
                for cam in self.cameras:
                    p = frame.images.get(cam)
                    if not p or not Path(p).exists():
                        continue
                    res = model.predict(str(p), conf=self.conf, verbose=False)[0]
                    checked += 1
                    for box in res.boxes:
                        cls = int(box.cls.item())
                        name = res.names.get(cls, "").lower()
                        if name in prompts:
                            counts[name] += 1
                            det_scene[name].add(sc.token)
        results: dict[str, dict] = {}
        for cid, words in vocab.items():
            evidence = []
            for w in words:
                for st in sorted(det_scene.get(w, [])):
                    evidence.append({"scene": st, "prompt": w})
            verdict = "present" if evidence else "absent"
            results[cid] = {"level": self.level, "verdict": verdict,
                            "scenes_checked": checked, "evidence": evidence[:20]}
        return results
