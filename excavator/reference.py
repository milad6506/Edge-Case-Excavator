"""Reference model loader: builds the case registry from reference/*.json.

Cases are the auditable units:
  ACTOR:<category>:<name>        actor sub-class presence
  MISBEHAVIOR:<TOKEN>            misbehavior regime token
  STATE:<category>:<machine>     signaling state machine
  FACTOR:<layer>.<sec>.<name>    ODD factor enum leaf
  BAND:<layer>.<sec>.<name>      ODD factor numeric band (edge mining)
  BUFFER:<text>                  statutory clearance buffer
  EXP:<expectation id>           behavioral expectation (trigger-driven)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Case:
    case_id: str
    kind: str                 # actor | misbehavior | state | factor | band | buffer | expectation
    name: str
    keywords: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def primary_pattern(self) -> re.Pattern:
        return _phrase_any(self.keywords)


def _words(text: str) -> list[str]:
    """Tokenize spec identifiers into plain words (CamelCase + underscores)."""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = text.replace("_", " ").replace("|", " ")
    return [w for w in re.findall(r"[A-Za-z0-9µ]+", text) if len(w) > 1 or w.isdigit()]


_GENERIC_WORDS = {
    "vehicle", "vehicles", "light", "lights", "state", "states", "type", "types",
    "sign", "signs", "signal", "signals", "marking", "markings", "official",
    "officials", "equipment", "operator", "operators", "passenger", "passengers",
    "zone", "zones", "area", "areas", "pedestrian", "pedestrians", "stage", "buffer",
    # numerals, sizes, colors, generic roles seen over-matching in QA corpora
    "one", "two", "three", "four", "five", "six", "seven", "eight", "ten",
    "large", "small", "heavy", "minor", "major", "scale",
    "rider", "riders", "riding", "mobile", "priority", "command", "unit", "units",
    "service", "patrol", "airport", "nearby", "standard", "general", "public",
    "commercial", "truck", "trucks", "yellow", "red", "green", "white", "black",
    "blue", "silver", "brown", "adult", "person", "persons",
}


def _phrase_any(keywords: list[str]) -> re.Pattern:
    """Match any keyword via: full phrase, adjacent bigrams, or a distinctive
    single token (recall-first; L1c close-reading restores precision)."""
    def _word(w: str) -> str:
        if w.isalpha() and len(w) >= 4 and w.endswith("s") and not w.endswith("ss"):
            return re.escape(w[:-1]) + r"(?:s|es)?"      # Strollers -> stroller(s)
        esc = re.escape(w)
        return esc + (r"(?:s|es)?" if w.isalpha() else "")

    alts: list[str] = []
    for kw in keywords:
        ws = _words(kw)
        if not ws:
            continue
        if len(ws) <= 2:
            alts.append(r"\b" + r"[\s\-]+".join(_word(w) for w in ws) + r"\b")
            continue
        alts.append(r"\b" + r"[\s\-]+".join(_word(w) for w in ws) + r"\b")
        for a, b in zip(ws, ws[1:]):
            if a.lower() in _GENERIC_WORDS and b.lower() in _GENERIC_WORDS:
                continue  # e.g. 'light vehicle' — too generic as a bigram
            alts.append(r"\b" + _word(a) + r"[\s\-]+" + _word(b) + r"\b")
        for w in ws:
            if len(w) >= 5 and w.isalpha() and w.lower() not in _GENERIC_WORDS:
                alts.append(r"\b" + _word(w) + r"\b")
    if not alts:
        alts.append(r"(?!x)x")  # never matches
    return re.compile("|".join(dict.fromkeys(alts)), re.IGNORECASE)


def _sub_class_kw(name: str, variants: str | None) -> list[str]:
    kws = [name]
    if variants:
        kws += [v.strip() for v in variants.split(",") if v.strip()]
    return kws


class Reference:
    def __init__(self, reference_dir: str | Path):
        ref = Path(reference_dir)
        self.taxonomy = json.loads((ref / "taxonomy_v6.json").read_text())
        self.expectations = json.loads((ref / "expectations_v2.json").read_text())
        self.version = self.taxonomy.get("version", "?")
        self.cases: list[Case] = []
        self._build_actor_cases()
        self._build_factor_cases()
        self._build_expectation_cases()

    # -- builders -----------------------------------------------------------
    def _build_actor_cases(self) -> None:
        for cat in self.taxonomy["actor_categories"]:
            cname = cat["name"]
            for sub in cat.get("sub_classes", []):
                kw = _sub_class_kw(sub["name"], sub.get("variants"))
                self.cases.append(Case(
                    case_id=f"ACTOR:{cat['actor_category']}:{sub['name']}",
                    kind="actor", name=sub["name"], keywords=kw,
                    meta={"category": cname, "bounds": sub.get("bounds"),
                          "variants": sub.get("variants")}))
            for grp in cat.get("misbehavior_regime", []):
                for tok in grp.get("tokens", []):
                    self.cases.append(Case(
                        case_id=f"MISBEHAVIOR:{tok['token']}",
                        kind="misbehavior", name=tok["token"],
                        keywords=[tok["token"], tok.get("description") or ""],
                        meta={"type": grp["type"], "group": grp["group"],
                              "category": cname}))
            for key, sm in (cat.get("state_machines") or {}).items():
                self.cases.append(Case(
                    case_id=f"STATE:{cat['actor_category']}:{key}",
                    kind="state", name=sm["name"], keywords=sm["values"],
                    meta={"category": cname, "values": sm["values"]}))

    def _build_factor_cases(self) -> None:
        for layer in self.taxonomy["factor_layers"]:
            for sec in layer.get("sections", []):
                loc = f"L{layer['layer_id']}.{sec['id']}"
                for item in sec.get("items", []):
                    label = item.get("name") or item.get("text", "")[:40]
                    base = f"{loc}.{item.get('name', 'buffer')}"
                    if item["type"] == "enum":
                        self.cases.append(Case(
                            case_id=f"FACTOR:{base}", kind="factor", name=item["name"],
                            keywords=item["values"],
                            meta={"layer": layer["layer_id"], "section": sec["id"],
                                  "values": item["values"]}))
                    elif item["type"] in ("band", "range", "kinematic"):
                        self.cases.append(Case(
                            case_id=f"BAND:{base}", kind="band", name=item["name"],
                            keywords=[item["name"]],
                            meta={"layer": layer["layer_id"], "section": sec["id"],
                                  "item": item}))
                    elif item["type"] == "buffer":
                        self.cases.append(Case(
                            case_id=f"BUFFER:{loc}.{len(self.cases)}", kind="buffer",
                            name=item["text"][:60], keywords=[item["text"]],
                            meta={"layer": layer["layer_id"], "section": sec["id"]}))

    def _build_expectation_cases(self) -> None:
        for e in self.expectations:
            kws = list(e.get("triggers") or [])
            if e.get("title"):
                kws.append(e["title"])
            self.cases.append(Case(
                case_id=f"EXP:{e['id']}", kind="expectation", name=e.get("title") or e["id"],
                keywords=kws,
                meta={"text": e.get("text"), "category": e.get("category"),
                      "sub_category": e.get("sub_category"),
                      "statutory_ref": e.get("statutory_ref"),
                      "source_framework": e.get("source_framework"),
                      "sequence": [s["act"] for s in e.get("meta_action_sequence", [])]}))

    # -- access -------------------------------------------------------------
    def filter(self, scope: str = "all", families: str = ".*") -> list[Case]:
        rx = re.compile(families)
        if scope == "leaves":
            kinds = {"actor", "misbehavior", "state", "factor", "band", "buffer"}
            return [c for c in self.cases if c.kind in kinds and rx.search(c.case_id)]
        if scope == "expectations":
            return [c for c in self.cases if c.kind == "expectation" and rx.search(c.case_id)]
        return [c for c in self.cases if rx.search(c.case_id)]

    def stats(self) -> dict:
        from collections import Counter
        return {"taxonomy_version": self.version,
                "expectations": len(self.expectations),
                "cases": dict(Counter(c.kind for c in self.cases))}
