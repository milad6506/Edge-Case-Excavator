"""DriveLM-nuScenes adapter.

Expects a DriveLM-style VQA export: {scene_token: {scene_description,
key_frames: {frame_token: {key_object_infos, QA, image_paths}}}}.
Images are resolved against the dataset root with sensible fallbacks.
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import BaseAdapter, Frame, Scene, TextRecord

_CAM_ORDER = ["CAM_FRONT", "CAM_FRONT_LEFT", "CAM_FRONT_RIGHT",
              "CAM_BACK_LEFT", "CAM_BACK", "CAM_BACK_RIGHT"]


class DriveLmAdapter(BaseAdapter):
    name = "drivelm"

    def _find_data_file(self) -> Path:
        if self.data_file:
            p = self.root / self.data_file
            if not p.exists():
                raise FileNotFoundError(p)
            return p
        candidates = sorted(self.root.glob("v1_*_train_nus*.json")) + \
            sorted(self.root.glob("v1_*_val_nus*.json"))
        if not candidates:
            raise FileNotFoundError(
                f"no DriveLM vqa json under {self.root}; pass --data-file")
        return candidates[0]

    def _resolve_image(self, json_dir: Path, rel: str) -> Path | None:
        rel = rel.replace("\\", "/")
        for cand in (self.root / rel, self.root.parent / rel,
                     json_dir / rel, json_dir.parent / rel):
            if cand.exists():
                return cand
        # last resort: search by basename under root
        base = Path(rel).name
        hits = list(self.root.glob(f"nuscenes/samples/*/{base}"))
        return hits[0] if hits else None

    def load(self, limit: int | None = None) -> list[Scene]:
        data_path = self._find_data_file()
        data = json.loads(data_path.read_text())
        scenes: list[Scene] = []
        for tok, s in data.items():
            sc = Scene(token=tok, name=s.get("scene_description", "")[:80])
            if s.get("scene_description"):
                sc.texts.append(TextRecord("scene_description", s["scene_description"]))
            for i, (ftok, fr) in enumerate(sorted(s.get("key_frames", {}).items())):
                frame = Frame(token=ftok, scene_token=tok, index=i)
                imgs = fr.get("image_paths") or {}
                for cam in _CAM_ORDER:
                    if cam in imgs:
                        p = self._resolve_image(data_path.parent, imgs[cam])
                        if p:
                            frame.images[cam] = p
                for qa_kind, items in (fr.get("QA") or {}).items():
                    for qa in items or []:
                        q, a = qa.get("Q") or "", qa.get("A") or ""
                        if q or a:
                            frame.texts.append(TextRecord("qa", f"{q} {a}"))
                for obj in (fr.get("key_object_infos") or {}).values():
                    desc = " ".join(str(obj.get(k, "")) for k in
                                    ("Category", "Status", "Visual_description"))
                    if desc.strip():
                        frame.texts.append(TextRecord("annotation", desc))
                sc.frames.append(frame)
            scenes.append(sc)
            if limit and len(scenes) >= limit:
                break
        return scenes


def register(registry: dict) -> None:
    registry["drivelm"] = DriveLmAdapter
