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
    """case_id -> detector prompt words, from ACTOR: cases only.

    Open-vocab detection needs noun phrases, not spec names: a curated map
    first (keyed by distinctive sub-strings of the case id), falling back to
    the spec-name words.
    """
    curated = [
        (("Passenger Light", "Sedans"), ["car", "sedan", "suv", "hatchback", "minivan"]),
        (("Pickup", "Utility Vans"), ["pickup truck", "van", "utility vehicle"]),
        (("Heavy Commercial", "Combination Trailers"), ["truck", "semi truck", "trailer", "lorry"]),
        (("Transit Buses", "Coaches"), ["bus", "city bus", "coach bus"]),
        (("School Buses",), ["school bus", "bus"]),
        (("Motorcycles, Mopeds", "Two-Wheelers"), ["motorcycle", "moped", "scooter"]),
        (("Emergency Priority", "Police", "Fire", "Ambulance"),
         ["police car", "fire truck", "ambulance", "emergency vehicle"]),
        (("Tow Trucks",), ["tow truck", "truck"]),
        (("Convertible", "Cabriolet"), ["convertible car", "car"]),
        (("Shuttle Vans", "Transit Passenger Vans"), ["van", "minivan", "shuttle bus"]),
        (("Sidecars", "Tricycles", "Three-Wheelers"), ["sidecar motorcycle", "tricycle", "motorcycle"]),
        (("Rescue Command", "Mobile Emergency Command"), ["emergency vehicle", "command vehicle", "truck"]),
        (("Farm Tractors", "Agricultural", "Construction Equipment"),
         ["tractor", "farm tractor", "construction vehicle", "excavator"]),
        (("Pedestrians Adult",), ["pedestrian", "person"]),
        (("Pedestrians Child", "Toddlers", "Children"), ["child", "kid", "person"]),
        (("Strollers", "Pushing Carts", "Bulky Objects"), ["stroller", "baby carriage", "person with cart"]),
        (("Traffic Police", "Flaggers", "Emergency Officials"), ["police officer", "traffic officer", "person"]),
        (("First Responders", "EMS"), ["firefighter", "paramedic", "emergency worker", "person"]),
        (("Grouped Pedestrian", "Processions", "Procession"), ["group of people", "crowd", "pedestrian"]),
        (("Accompanied Supervisors", "Crossing Guards"), ["crossing guard", "person with children"]),
        (("Reduced Mobility", "Wheelchair", "Visually Impaired"),
         ["wheelchair", "person in wheelchair", "blind person", "person with cane"]),
        (("Bicyclists", "Commuter Cyclists"), ["cyclist", "person on bicycle", "bicycle"]),
        (("Recumbent Cyclists", "Cargo Bikes"), ["cargo bike", "recumbent bicycle", "cyclist"]),
        (("Electric Scooter", "Micro-Mobility"), ["kick scooter", "e-scooter rider", "person on scooter"]),
        (("Transit Passengers", "Boarding", "Alighting"), ["person boarding bus", "pedestrian", "person"]),
        (("Intoxicated", "Impaired", "Incapacitated"), ["stumbling person", "pedestrian", "person"]),
        (("Person Pushing or Pulling",), ["person pushing bicycle", "person pulling cart", "person"]),
        (("Roadway-Maintenance", "Utility Personnel", "Construction Flaggers"),
         ["construction worker", "road worker", "person with safety vest"]),
        (("Tow-Truck Operators", "Roadside Assistance"), ["mechanic", "roadside worker", "person"]),
        (("Vehicle Cabin Passengers", "Occupants"), ["car passenger", "person in car"]),
        (("Domestic Pets", "Dogs", "Cats"), ["dog", "cat"]),
        (("Large Wild Animals", "Deer", "Elk", "Moose"), ["deer", "elk", "moose", "wild animal"]),
        (("Mounted Horses", "Herded Livestock", "Cattle", "Sheep"), ["horse", "cow", "cattle", "sheep"]),
        (("Animal-Drawn Carriages", "Buggies", "Equestrian"), ["horse carriage", "horse and buggy", "horse"]),
        (("Fallen Cargo", "Road Debris"), ["debris", "road debris", "fallen objects"]),
        (("Fallen Trees", "Branches", "Utility Wires"), ["fallen tree", "tree branch", "debris"]),
        (("Stationary Disabled Vehicles", "Crashed Wrecks"), ["broken down car", "wreck", "abandoned car"]),
        (("Construction Channelization", "Cones", "Barricades", "Arrow Boards"),
         ["traffic cone", "barrier", "construction barrel", "roadblock"]),
        (("Freight Trains", "Heavy Rail"), ["freight train", "train"]),
        (("Passenger Commuter Trains", "High-Speed Passenger Rail"), ["passenger train", "train"]),
        (("Passenger Streetcars", "Trams", "Light Rail"), ["tram", "streetcar", "light rail train"]),
        (("Railway Crew", "Switchmen", "Motormen"), ["train worker", "railway worker", "person"]),
    ]
    vocab = {}
    for c in cases:
        if c.kind != "actor":
            continue
        prompts = None
        for keys, ps in curated:
            if any(k in c.name for k in keys):
                prompts = ps
                break
        if prompts is None:
            words = [w.lower() for w in re.findall(r"[A-Za-z]+", c.name)]
            prompts = words or [c.name.lower()]
        vocab[c.case_id] = prompts
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
        # a prompt used by several classes cannot attribute detections uniquely;
        # only exclusive prompts count toward a specific case's presence.
        prompt_users: dict[str, list[str]] = defaultdict(list)
        for cid, words in vocab.items():
            for w in words:
                prompt_users[w].append(cid)
        exclusive = {cid: [w for w in words if len(prompt_users[w]) == 1]
                     for cid, words in vocab.items()}
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
            for w in exclusive[cid]:
                for st in sorted(det_scene.get(w, [])):
                    evidence.append({"scene": st, "prompt": w})
            verdict = "present" if evidence else ("absent" if exclusive[cid] else "not_run")
            results[cid] = {"level": self.level, "verdict": verdict,
                            "scenes_checked": checked, "evidence": evidence[:20]}
        return results
